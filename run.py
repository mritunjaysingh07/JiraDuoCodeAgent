from jira_gitlab_agent import JiraGitlabAgent
from dotenv import load_dotenv
import os
import argparse
import logging
import sys
from pathlib import Path

def setup_logging(log_file: str = "logs/agent.log"):
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def validate_environment():
    """Validate required environment variables."""
    required_vars = {
        'JIRA_URL': 'Jira instance URL',
        'JIRA_USERNAME': 'Jira username',
        'JIRA_API_TOKEN': 'Jira API token',
        'GITLAB_URL': 'GitLab instance URL',
        'GITLAB_TOKEN': 'GitLab API token'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        print("\nPlease set these variables in your .env file or environment.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Process Jira stories with GitLab Duo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Process a single story:
    python run.py PROJ-123 12345

  Process multiple stories:
    python run.py --batch stories.txt 12345

  Use custom configuration:
    python run.py --config custom_config.yaml PROJ-123 12345

  Use specific base branch:
    python run.py --base-branch develop PROJ-123 12345
        """
    )
    
    # Story selection arguments
    story_group = parser.add_mutually_exclusive_group(required=True)
    story_group.add_argument('issue_key', nargs='?', help='Jira issue key (e.g., PROJ-123)')
    story_group.add_argument('--batch', help='Path to file containing list of Jira issue keys')
    
    # Required arguments
    parser.add_argument('project_id', type=int, help='GitLab project ID')
    
    # Optional arguments
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    parser.add_argument('--base-branch', help='Base branch for new feature branches')
    parser.add_argument('--log-file', default='logs/agent.log', help='Path to log file')
    
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_file)
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Validate environment
    validate_environment()
    
    try:
        # Initialize agent
        agent = JiraGitlabAgent(
            jira_url=os.getenv("JIRA_URL"),
            jira_username=os.getenv("JIRA_USERNAME"),
            jira_api_token=os.getenv("JIRA_API_TOKEN"),
            gitlab_url=os.getenv("GITLAB_URL"),
            gitlab_token=os.getenv("GITLAB_TOKEN"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            config_path=args.config
        )
        
        # Process stories
        if args.batch:
            # Process multiple stories from file
            try:
                with open(args.batch, 'r') as f:
                    issue_keys = [line.strip() for line in f if line.strip()]
            except Exception as e:
                logger.error(f"Failed to read batch file: {str(e)}")
                return 1
            
            results = []
            for issue_key in issue_keys:
                logger.info(f"Processing story {issue_key}")
                result = agent.process_jira_story(
                    issue_key=issue_key,
                    project_id=args.project_id,
                    base_branch=args.base_branch
                )
                results.append((issue_key, result))
            
            # Print batch results
            print("\n=== Batch Processing Results ===")
            for issue_key, result in results:
                print(f"\n{issue_key}:")
                print(f"Status: {result['status']}")
                if result['status'] == 'success':
                    print(f"Merge Request: {result['merge_request']['merge_request_url']}")
                else:
                    print(f"Error: {result['error']}")
        
        else:
            # Process single story
            result = agent.process_jira_story(
                issue_key=args.issue_key,
                project_id=args.project_id,
                base_branch=args.base_branch
            )
            
            # Print result
            print("\n=== Processing Results ===")
            print(f"Status: {result['status']}")
            
            if result['status'] == 'success':
                print(f"\nStory Details:")
                print(f"- Key: {result['story']['key']}")
                print(f"- Summary: {result['story']['summary']}")
                print(f"- Priority: {result['story']['priority']}")
                print(f"- Story Points: {result['story']['story_points']}")
                
                print(f"\nGitLab Details:")
                print(f"- Branch: {result['branch']}")
                print(f"- Merge Request: {result['merge_request']['merge_request_url']}")
            else:
                print(f"\nError: {result['error']}")
                return 1

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main()) 