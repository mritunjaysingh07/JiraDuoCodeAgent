import os
from dotenv import load_dotenv
load_dotenv()
from jira import JIRA
import gitlab
from typing import Dict, List, Optional, Any, Tuple
import requests
import openai
import yaml
import logging
from pathlib import Path
import time
from datetime import datetime
import sys

class ProgressTracker:
    """Track and update progress in merge requests automatically."""

    def __init__(self, gitlab_client, project_id: int, mr_iid: int):
        import logging
        self.logger = logging.getLogger("jira_gitlab_agent.ProgressTracker")
        self.gitlab = gitlab_client
        self.project_id = project_id
        self.mr_iid = mr_iid
        self.project = self.gitlab.projects.get(project_id)
        self.mr = self.project.mergerequests.get(mr_iid)
        
    def _parse_progress_section(self, description: str) -> dict:
        """Parse progress section from merge request description."""
        progress = {
            'setup': False,
            'implementation': False,
            'tests': False,
            'documentation': False,
            'review': False,
            'acceptance': False
        }
        
        try:
            # Find progress section
            start = description.find('## Progress Tracking')
            if start == -1:
                return progress
                
            end = description.find('##', start + 1)
            if end == -1:
                progress_section = description[start:]
            else:
                progress_section = description[start:end]
                
            # Parse checkboxes
            for line in progress_section.split('\n'):
                if '- [x]' in line.lower():
                    if 'setup' in line.lower():
                        progress['setup'] = True
                    elif 'implementation' in line.lower():
                        progress['implementation'] = True
                    elif 'test' in line.lower():
                        progress['tests'] = True
                    elif 'documentation' in line.lower():
                        progress['documentation'] = True
                    elif 'review' in line.lower():
                        progress['review'] = True
                    elif 'acceptance' in line.lower():
                        progress['acceptance'] = True
                        
            return progress
        except Exception as e:
            self.logger.error(f"Error parsing progress section: {str(e)}")
            return progress

    def _update_progress_section(self, description: str, progress: dict) -> str:
        """Update progress section in merge request description."""
        try:
            start = description.find('## Progress Tracking')
            if start == -1:
                return description
                
            end = description.find('##', start + 1)
            if end == -1:
                before_progress = description[:start]
                after_progress = ""
            else:
                before_progress = description[:start]
                after_progress = description[end:]
                
            # Create updated progress section
            progress_section = "## Progress Tracking\n"
            progress_section += f"- [{'x' if progress['setup'] else ' '}] Initial setup complete\n"
            progress_section += f"- [{'x' if progress['implementation'] else ' '}] Core functionality implemented\n"
            progress_section += f"- [{'x' if progress['tests'] else ' '}] Tests added and passing\n"
            progress_section += f"- [{'x' if progress['documentation'] else ' '}] Documentation complete\n"
            progress_section += f"- [{'x' if progress['review'] else ' '}] Code reviewed\n"
            progress_section += f"- [{'x' if progress['acceptance'] else ' '}] Acceptance criteria met\n\n"
            
            return before_progress + progress_section + after_progress
            
        except Exception as e:
            self.logger.error(f"Error updating progress section: {str(e)}")
            return description

    def check_structure_progress(self) -> bool:
        """Check if initial structure is complete."""
        try:
            # Check for essential files and directories
            tree = self.project.repository_tree(ref=self.mr.source_branch, recursive=True)
            required_patterns = [
                'src/',
                'tests/',
                '__init__.py',
                'requirements.txt',
                'README.md'
            ]
            
            files = [item['path'] for item in tree]
            return all(any(f.endswith(pattern.strip('/')) for f in files) for pattern in required_patterns)
        except Exception as e:
            self.logger.error(f"Error checking structure progress: {str(e)}")
            return False

    def check_implementation_progress(self) -> bool:
        """Check if core implementation is complete."""
        try:
            # Check for implementation files and content
            changes = self.mr.changes()
            implementation_files = [change['new_path'] for change in changes['changes'] 
                                 if change['new_path'].endswith(('.py', '.js', '.ts', '.java'))]
            
            return len(implementation_files) > 0
        except Exception as e:
            self.logger.error(f"Error checking implementation progress: {str(e)}")
            return False

    def check_test_progress(self) -> bool:
        """Check if tests are added and passing."""
        try:
            # Check for test files
            tree = self.project.repository_tree(ref=self.mr.source_branch, path='tests', recursive=True)
            test_files = [item['path'] for item in tree if item['path'].startswith('test_')]
            
            # Check pipeline status
            if hasattr(self.mr, 'pipeline') and self.mr.pipeline:
                return len(test_files) > 0 and self.mr.pipeline['status'] == 'success'
            
            return len(test_files) > 0
        except Exception as e:
            self.logger.error(f"Error checking test progress: {str(e)}")
            return False

    def check_documentation_progress(self) -> bool:
        """Check if documentation is complete."""
        try:
            # Check for documentation files and README updates
            tree = self.project.repository_tree(ref=self.mr.source_branch, recursive=True)
            doc_files = [item['path'] for item in tree if item['path'].endswith(('.md', '.rst', '.txt'))]
            
            # Check for docstrings in Python files
            changes = self.mr.changes()
            python_files = [change['new_path'] for change in changes['changes'] 
                          if change['new_path'].endswith('.py')]
            
            return len(doc_files) > 0 and len(python_files) > 0
        except Exception as e:
            self.logger.error(f"Error checking documentation progress: {str(e)}")
            return False

    def check_review_progress(self) -> bool:
        """Check if code review is complete."""
        try:
            # Check for approvals and resolved discussions
            approvals = self.mr.approvals.get()
            discussions = self.mr.discussions.list()
            
            has_approvals = len(approvals.approved_by) > 0
            all_discussions_resolved = all(
                discussion.attributes['resolved'] 
                for discussion in discussions 
                if hasattr(discussion, 'resolved')
            )
            
            return has_approvals and all_discussions_resolved
        except Exception as e:
            self.logger.error(f"Error checking review progress: {str(e)}")
            return False

    def update_progress(self) -> dict:
        """Update progress tracking in merge request."""
        try:
            # Get current description and progress
            description = self.mr.description
            current_progress = self._parse_progress_section(description)
            
            # Check each progress item
            new_progress = {
                'setup': self.check_structure_progress(),
                'implementation': self.check_implementation_progress(),
                'tests': self.check_test_progress(),
                'documentation': self.check_documentation_progress(),
                'review': self.check_review_progress(),
                'acceptance': current_progress['acceptance']  # Keep existing acceptance status
            }
            
            # Update description if progress changed
            if new_progress != current_progress:
                updated_description = self._update_progress_section(description, new_progress)
                self.mr.description = updated_description
                self.mr.save()
                
            return new_progress
            
        except Exception as e:
            self.logger.error(f"Error updating progress: {str(e)}")
            return {}

class JiraGitlabAgent:
    def __init__(self, 
                 jira_url: str,
                 jira_username: str,
                 jira_api_token: str,
                 gitlab_url: str,
                 gitlab_token: str,
                 openai_api_key: str = None,
                 config_path: str = "config/config.yaml"):
        """Initialize the Jira-GitLab integration agent."""
        # Setup logging first
        self._setup_logging(config_path)
        
        self.logger.info("Initializing Jira-GitLab Agent...")
        
        # Initialize clients
        self._init_jira_client(jira_url, jira_username, jira_api_token)
        self._init_gitlab_client(gitlab_url, gitlab_token)
        
        # Store configuration
        self.config = self.load_config(config_path)
        
        # Initialize OpenAI if LLM refinement is enabled
        self._init_llm(openai_api_key)
        
        self.logger.info("Agent initialization completed successfully")

    def _setup_logging(self, config_path: str) -> None:
        """Setup logging configuration."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            log_config = config.get('logging', {})
            log_file = log_config.get('file', 'logs/agent.log')
            
            # Create logs directory if it doesn't exist
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            
            logging.basicConfig(
                level=getattr(logging, log_config.get('level', 'INFO')),
                format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
        except Exception as e:
            # Fallback to basic logging if config fails
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            self.logger.warning(f"Failed to setup logging from config: {str(e)}")

    def _init_jira_client(self, url: str, username: str, token: str) -> None:
        """Initialize Jira client with error handling."""
        try:
            self.jira = JIRA(
                server=url,
                basic_auth=(username, token)
            )
            self.jira_url = url
            self.logger.info("Jira client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Jira client: {str(e)}")
            raise

    def _init_gitlab_client(self, url: str, token: str) -> None:
        """Initialize GitLab client with error handling and connection testing."""
        try:
            # Convert gitlab.com URL to API URL if needed
            if 'gitlab.com' in url:
                api_url = 'https://gitlab.com/api/v4'
            else:
                api_url = url.rstrip('/') + '/api/v4'
            
            self.gitlab = gitlab.Gitlab(url, private_token=token)
            
            # Set custom headers after initialization
            self.gitlab.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
                'DNT': '1'
            })
            
            # Test authentication and get user info
            try:
                self.gitlab.auth()
                current_user = self.gitlab.user
                self.logger.info(f"Authenticated as GitLab user: {current_user.username}")
            except Exception as e:
                self.logger.error(f"Failed to authenticate with GitLab: {str(e)}")
                raise
            
            self.gitlab_url = url.rstrip('/')
            self.gitlab_token = token
            self.logger.info("GitLab client initialized successfully")
        except gitlab.exceptions.GitlabAuthenticationError as e:
            self.logger.error(f"GitLab authentication failed. Please check your token: {str(e)}")
            raise
        except gitlab.exceptions.GitlabError as e:
            self.logger.error(f"GitLab API error: {str(e)}")
            raise
        except requests.exceptions.SSLError as e:
            self.logger.error(f"SSL verification failed. If using self-signed certificates, set ssl_verify=False: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize GitLab client: {str(e)}")
            raise

    def _init_llm(self, api_key: Optional[str]) -> None:
        """Initialize LLM configuration."""
        if self.is_llm_enabled():
            if api_key:
                openai.api_key = api_key
                self.logger.info("LLM-based prompt refinement enabled")
            else:
                self.logger.warning("LLM refinement enabled but no API key provided")
        else:
            self.logger.info("Using base prompts (LLM refinement disabled)")

    def load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file with validation."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate required sections
            required_sections = ['features', 'prompts', 'logging']
            missing_sections = [s for s in required_sections if s not in config]
            
            if missing_sections:
                raise ValueError(f"Missing required config sections: {missing_sections}")
            
            return config
        except Exception as e:
            self.logger.error(f"Failed to load config from {config_path}: {str(e)}")
            # Return default configuration
            return {
                'features': {
                    'llm_refinement': {'enabled': False},
                    'gitlab_duo': {'enabled': True, 'default_branch': 'main'},
                    'jira_integration': {'update_status': False}
                },
                'prompts': {'base': {}},
                'logging': {'level': 'INFO', 'prompt_refinement': True}
            }

    def is_llm_enabled(self) -> bool:
        """Check if LLM refinement is enabled in config."""
        return (self.config.get('features', {})
                .get('llm_refinement', {})
                .get('enabled', False))

    def get_base_prompt(self, prompt_type: str) -> str:
        """Get base prompt from configuration."""
        return (self.config.get('prompts', {})
                .get('base', {})
                .get(prompt_type, ''))

    def get_jira_story(self, issue_key: str) -> Dict:
        """Fetch a Jira story with enhanced error handling and retries."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Fetching Jira story {issue_key} (attempt {attempt + 1}/{max_retries})")
                issue = self.jira.issue(issue_key)
                
                # Get custom field IDs from config
                story_points_field = self.config['features']['jira_integration'].get('story_points_field', 'customfield_story_points')
                acceptance_criteria_field = self.config['features']['jira_integration'].get('acceptance_criteria_field', 'customfield_acceptance_criteria')
                
                story_data = {
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'description': issue.fields.description or '',
                    'status': issue.fields.status.name,
                    'acceptance_criteria': getattr(issue.fields, acceptance_criteria_field, '') or '',
                    'story_points': getattr(issue.fields, story_points_field, None),
                    'priority': getattr(issue.fields, 'priority', '').name if hasattr(issue.fields, 'priority') else 'Medium',
                    'components': [c.name for c in issue.fields.components] if hasattr(issue.fields, 'components') else [],
                    'labels': issue.fields.labels if hasattr(issue.fields, 'labels') else []
                }
                
                self.logger.info(f"Successfully fetched Jira story {issue_key}")
                return story_data
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.logger.error(f"Failed to fetch Jira story after {max_retries} attempts")
                    raise Exception(f"Error fetching Jira story: {str(e)}")

    def update_jira_status(self, issue_key: str, status: str) -> None:
        """Update Jira issue status if enabled in config."""
        if not self.config['features']['jira_integration'].get('update_status', False):
            return
        
        try:
            status_mapping = self.config['features']['jira_integration']['status_mapping']
            new_status = status_mapping.get(status.lower())
            
            if not new_status:
                self.logger.warning(f"No mapping found for status: {status}")
                return
            
            issue = self.jira.issue(issue_key)
            transitions = self.jira.transitions(issue)
            
            for t in transitions:
                if t['to']['name'].lower() == new_status.lower():
                    self.jira.transition_issue(issue, t['id'])
                    self.logger.info(f"Updated {issue_key} status to {new_status}")
                    return
            
            self.logger.warning(f"No valid transition found for status: {new_status}")
            
        except Exception as e:
            self.logger.error(f"Failed to update Jira status: {str(e)}")

    def create_gitlab_branch(self, project_id: int, branch_name: str, ref: str = None) -> str:
        """Create a new branch in GitLab with retries."""
        if ref is None:
            ref = self.config['features']['gitlab_duo'].get('default_branch', 'main')

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Creating GitLab branch {branch_name} (attempt {attempt + 1}/{max_retries})")
                project = self.gitlab.projects.get(project_id)
                # Check if branch already exists
                try:
                    branch = project.branches.get(branch_name)
                    self.logger.info(f"Branch {branch_name} already exists.")
                    return branch.name
                except gitlab.exceptions.GitlabGetError:
                    # Branch does not exist, so create it
                    branch = project.branches.create({
                        'branch': branch_name,
                        'ref': ref
                    })
                    self.logger.info(f"Successfully created branch: {branch_name}")
                    return branch.name

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.logger.error(f"Failed to create GitLab branch after {max_retries} attempts")
                    raise Exception(f"Error creating GitLab branch: {str(e)}")

    def refine_prompt_with_llm(self, story_details: Dict, prompt_type: str) -> str:
        """Use LLM to refine prompts based on story context and configuration."""
        base_prompt = self.get_base_prompt(prompt_type)
        
        if not self.is_llm_enabled():
            self.logger.debug(f"Using base prompt for {prompt_type}")
            return base_prompt

        try:
            if not openai.api_key:
                raise Exception("OpenAI API key not configured")

            llm_config = self.config['features']['llm_refinement']
            # Only allow keys that OpenAI expects
            allowed_keys = {'model', 'temperature', 'max_tokens'}
            llm_config = {k: v for k, v in llm_config.items() if k in allowed_keys}

            # Format the refinement prompt
            refinement_prompt = self.config['llm']['refinement_prompt'].format(
                key=story_details['key'],
                summary=story_details['summary'],
                description=story_details['description'],
                acceptance_criteria=story_details['acceptance_criteria'],
                base_prompt=base_prompt
            )

            # Initialize OpenAI client (no proxies argument)
            print("llm_config:", llm_config)
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model=llm_config.get('model', 'gpt-4'),
                messages=[
                    {"role": "system", "content": self.config['llm']['system_prompt']},
                    {"role": "user", "content": refinement_prompt}
                ],
                temperature=llm_config.get('temperature', 0.1),
                max_tokens=llm_config.get('max_tokens', 2000)
            )

            refined_prompt = response.choices[0].message.content

            
            self.logger.info(f"Successfully refined {prompt_type} prompt")
            self.logger.debug(f"Refined prompt: {refined_prompt}")
                

            return refined_prompt

        except Exception as e:
            self.logger.error(f"LLM refinement failed: {str(e)}")
            if llm_config.get('fallback_to_base', True):
                self.logger.info("Falling back to base prompt")
                return base_prompt
            raise

    def generate_mr_description(self, story_details: Dict) -> str:
        """Generate a structured merge request description with configurable prompt refinement."""
        try:
            # Get prompts for each section
            prompts = {}
            for prompt_type in self.config['features']['llm_refinement']['prompt_types']:
                prompts[prompt_type] = self.refine_prompt_with_llm(story_details, prompt_type)

            # Generate merge request description
            return f"""# Implementation: {story_details['summary']}

## Story Details
- **Jira Issue**: [{story_details['key']}]
- **Summary**: {story_details['summary']}
- **Priority**: {story_details['priority']}
- **Story Points**: {story_details['story_points'] or 'Not specified'}
- **Components**: {', '.join(story_details['components'])}
- **Labels**: {', '.join(story_details['labels'])}

## Requirements
{story_details['description']}

## Acceptance Criteria
{story_details['acceptance_criteria']}

## GitLab Duo Instructions

### 1. Generate Initial Structure
```
{prompts['structure']}
```

### 2. Implement Core Functionality
```
{prompts['implementation']}
```

### 3. Add Tests
```
{prompts['tests']}
```

### 4. Add Documentation
```
{prompts['documentation']}
```

### 5. Code Review
```
{prompts['review']}
```

## Implementation Steps

1. **Initial Setup**
   ```bash
   # Copy and paste the structure prompt above
   # Review and adjust the generated structure
   ```

2. **Core Implementation**
   ```bash
   # Copy and paste the implementation prompt above
   # Review and iterate on the implementation
   ```

3. **Testing**
   ```bash
   # Copy and paste the tests prompt above
   # Enhance test coverage as needed
   ```

4. **Documentation**
   ```bash
   # Copy and paste the documentation prompt above
   # Review and enhance documentation
   ```

## Progress Tracking
- [ ] Initial setup complete
- [ ] Core functionality implemented
- [ ] Tests added and passing
- [ ] Documentation complete
- [ ] Code reviewed
- [ ] Acceptance criteria met

## Notes for Reviewers
1. Verify all acceptance criteria are met
2. Check test coverage
3. Review error handling
4. Validate against requirements
5. Check code quality and best practices

## Related Links
- Jira Story: [{story_details['key']}]({self.jira_url}/browse/{story_details['key']})
- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        except Exception as e:
            self.logger.error(f"Failed to generate MR description: {str(e)}")
            raise

    def create_duo_merge_request(self, 
                                project_id: int, 
                                story_details: Dict, 
                                source_branch: str,
                                target_branch: str = None) -> Dict:
        """Create a merge request with GitLab Duo prompts."""
        if target_branch is None:
            target_branch = self.config['features']['gitlab_duo'].get('default_branch', 'main')
        try:
            project = self.gitlab.projects.get(project_id)
            # Check for existing open MR from this source branch
            existing_mrs = project.mergerequests.list(state='opened', source_branch=source_branch)
            if existing_mrs:
                mr = existing_mrs[0]
                self.logger.info(f"Reusing existing merge request: {mr.web_url}")
            else:
                # Get labels from config
                labels = self.config['features']['gitlab_duo'].get('labels', [])
                labels.append(story_details['key'])
                # Create merge request
                mr = project.mergerequests.create({
                    'source_branch': source_branch,
                    'target_branch': target_branch,
                    'title': f"Implement {story_details['key']}: {story_details['summary']}",
                    'description': self.generate_mr_description(story_details),
                    'labels': labels,
                    'remove_source_branch': True,
                    'squash': True
                })
                self.logger.info(f"Created merge request: {mr.web_url}")

            # Initialize progress tracker
            tracker = ProgressTracker(self.gitlab, project_id, mr.iid)
            initial_progress = tracker.update_progress()
            self.logger.info(f"Initial progress tracking set up: {initial_progress}")
            self.update_jira_status(story_details['key'], 'in_review')
            return {
                'merge_request_id': mr.iid,
                'merge_request_url': mr.web_url,
                'status': 'created' if not existing_mrs else 'existing',
                'progress': initial_progress
            }
        except Exception as e:
            self.logger.error(f"Failed to create merge request: {str(e)}")
            raise Exception(f"Error creating merge request: {str(e)}")

    def update_merge_request_progress(self, project_id: int, mr_iid: int) -> Dict:
        """Update progress tracking for a merge request."""
        try:
            tracker = ProgressTracker(self.gitlab, project_id, mr_iid)
            progress = tracker.update_progress()
            self.logger.info(f"Updated progress tracking: {progress}")
            return progress
        except Exception as e:
            self.logger.error(f"Failed to update merge request progress: {str(e)}")
            return {}

    def process_jira_story(self, 
                          issue_key: str, 
                          project_id: int,
                          base_branch: str = None) -> Dict:
        """Process a Jira story by creating a merge request with Duo prompts."""
        self.logger.info(f"Processing Jira story: {issue_key}")
        
        try:
            # 1. Fetch Jira story
            story = self.get_jira_story(issue_key)
            
            # 2. Update Jira status to in progress
            self.update_jira_status(issue_key, 'in_progress')
            
            # 3. Create GitLab branch
            branch_name = f"feature/{issue_key.lower()}"
            self.create_gitlab_branch(project_id, branch_name, base_branch)
            
            # 4. Create merge request with Duo prompts
            mr_details = self.create_duo_merge_request(
                project_id=project_id,
                story_details=story,
                source_branch=branch_name,
                target_branch=base_branch
            )
            
            self.logger.info(f"Successfully processed story {issue_key}")
            
            return {
                'status': 'success',
                'story': story,
                'branch': branch_name,
                'merge_request': mr_details
            }
        except Exception as e:
            self.logger.error(f"Failed to process story {issue_key}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

if __name__ == "__main__":
    # Example usage
    agent = JiraGitlabAgent(
        jira_url=os.getenv("JIRA_URL"),
        jira_username=os.getenv("JIRA_USERNAME"),
        jira_api_token=os.getenv("JIRA_API_TOKEN"),
        gitlab_url=os.getenv("GITLAB_URL"),
        gitlab_token=os.getenv("GITLAB_TOKEN"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),  # Optional: for prompt refinement
        config_path=os.getenv("CONFIG_PATH", "config/config.yaml")
    )

    # Use command-line arguments if provided
    issue_key = sys.argv[1] if len(sys.argv) > 1 else "SCRUM-198"
    project_id = int(sys.argv[2]) if len(sys.argv) > 2 else 70711337

    print("GITLAB_URL:", os.getenv("GITLAB_URL"))
    print("GITLAB_TOKEN:", os.getenv("GITLAB_TOKEN"))
    print("PROJECT_ID:", project_id)

    result = agent.process_jira_story(
        issue_key=issue_key,
        project_id=project_id
    )
    print(result)