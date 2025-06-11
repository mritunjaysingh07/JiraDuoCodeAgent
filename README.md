# Jira-GitLab Duo Integration Agent

An intelligent integration agent that automates code generation by connecting Jira stories with GitLab Duo, featuring optional LLM-powered prompt refinement and automated progress tracking.

## Features

- 🔄 Automated workflow from Jira stories to GitLab merge requests
- 🤖 GitLab Duo integration for AI-assisted code generation
- 🧠 Optional LLM-powered prompt refinement (using OpenAI GPT-4)
- ⚙️ Configurable feature switches and base prompts
- 📝 Structured merge request templates
- 📊 Automated progress tracking
- 🔍 Comprehensive logging

## Prerequisites

- Python 3.8+
- Jira account with API access
- GitLab account with API access
- OpenAI API key (optional, for LLM prompt refinement)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Jira-GitlabDuo.git
cd Jira-GitlabDuo
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the project root:
```env
JIRA_URL=https://your-jira-instance.com
JIRA_USERNAME=your_username
JIRA_API_TOKEN=your_jira_api_token
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_gitlab_token
OPENAI_API_KEY=your_openai_api_key  # Optional: for LLM prompt refinement
```

2. Configure feature switches in `config/config.yaml`:
```yaml
features:
  llm_refinement:
    enabled: false  # Set to true to enable LLM-based prompt refinement
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 1000
    fallback_to_base: true
```

### LLM Feature Switch

The agent supports two modes for generating GitLab Duo prompts:

1. **Base Prompts** (Default)
   - Uses predefined prompts from `config/config.yaml`
   - No external API calls required
   - Faster execution

2. **LLM-Refined Prompts**
   - Uses OpenAI GPT-4 to enhance prompts based on story context
   - Requires OpenAI API key
   - More contextual and specific prompts

To switch between modes:
1. Open `config/config.yaml`
2. Set `features.llm_refinement.enabled` to `true` or `false`
3. Configure other LLM parameters as needed

## Usage

### Command Line Interface

The agent provides a rich command-line interface through `run.py` with various options for processing Jira stories:

```bash
# Process a single story
python run.py PROJ-123 12345

# Process multiple stories from a file
python run.py --batch stories.txt 12345

# Use custom configuration file
python run.py --config custom_config.yaml PROJ-123 12345

# Use specific base branch
python run.py --base-branch develop PROJ-123 12345

# Specify custom log file location
python run.py --log-file logs/custom.log PROJ-123 12345
```

#### Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `issue_key` | Single Jira issue key to process | `PROJ-123` |
| `--batch` | Path to file containing list of Jira issue keys | `--batch stories.txt` |
| `project_id` | GitLab project ID (required) | `12345` |
| `--config` | Path to custom config file | `--config custom_config.yaml` |
| `--base-branch` | Base branch for new feature branches | `--base-branch develop` |
| `--log-file` | Path to log file | `--log-file logs/custom.log` |

#### Batch Processing
For batch processing, create a text file with one Jira issue key per line:
```text
PROJ-123
PROJ-124
PROJ-125
```

Then run:
```bash
python run.py --batch stories.txt 12345
```

### Progress Tracking

The agent automatically tracks progress for each merge request across multiple dimensions:

1. **Setup Progress**
   - Checks for essential files and directories
   - Verifies project structure

2. **Implementation Progress**
   - Monitors code changes
   - Tracks implementation file additions

3. **Test Progress**
   - Verifies test file existence
   - Monitors CI pipeline status

4. **Documentation Progress**
   - Checks documentation files
   - Verifies docstring presence

5. **Review Progress**
   - Tracks code review approvals
   - Monitors discussion resolution

6. **Acceptance Progress**
   - Managed through manual verification

Progress is displayed in the merge request description and automatically updated as changes occur.

### Implementation Details

The agent is structured into several key components:

1. **Jira Integration**
   - Fetches story details
   - Updates story status
   - Tracks story progress

2. **GitLab Integration**
   - Creates feature branches
   - Generates merge requests
   - Manages Duo prompts
   - Tracks progress

3. **Progress Tracker**
   - Monitors implementation status
   - Updates merge request description
   - Provides progress metrics

4. **Configuration System**
   - Feature toggles
   - Environment variables
   - Customizable templates

5. **Logging System**
   - File and console logging
   - Configurable log levels
   - Detailed operation tracking

### Environment Setup

Required environment variables in `.env`:
```env
JIRA_URL=https://your-jira-instance.com
JIRA_USERNAME=your_username
JIRA_API_TOKEN=your_jira_api_token
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_gitlab_token
OPENAI_API_KEY=your_openai_api_key  # Optional: for LLM prompt refinement
```

### Error Handling

The agent includes comprehensive error handling:
- Environment validation
- API connection errors
- File operation errors
- Progress tracking issues
- User interruptions

Errors are:
1. Logged to file and console
2. Reported in command output
3. Reflected in return status

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# Follow below steps
   1. Open the merge request URL
   2. Find the "GitLab Duo Instructions" section
   3. Start with "1. Generate Initial Structure"
   4. Copy the entire prompt (including /duo command)
   5. Paste it in the MR discussion
   6. Wait for Duo's response
   7. Review and commit the code
   8. Move to the next prompt

## Using GitLab Duo in Merge Requests

### Understanding Merge Request Discussions

When a merge request is created, you'll interact with GitLab Duo through the merge request's discussion feature. Here's how:

1. **Accessing the Discussion**
   - Open your merge request in GitLab
   - Look for the "Discussion" tab or scroll down to the discussion section
   - This is where you'll communicate with GitLab Duo

2. **Using Duo Commands**
   - Each prompt in the merge request template starts with `/duo`
   - These are special commands that activate GitLab Duo
   - Example: `/duo Please create a basic authentication system using JWT`

3. **Step-by-Step Process**
   ```
   a. Open the merge request URL from the agent's output
   b. Scroll to the discussion section
   c. Find the "GitLab Duo Instructions" section in the MR description
   d. Copy the first prompt (including the /duo command)
   e. Click the "Start discussion" or "Comment" button
   f. Paste the entire prompt into the discussion box
   g. Click "Comment" to send the prompt to GitLab Duo
   ```

4. **Working with Duo's Response**
   - Duo will respond in the same discussion thread
   - Review the generated code
   - Use GitLab's Web IDE to apply or modify the suggestions
   - Commit the changes when satisfied

### Example Interaction

```
[You]
/duo Please implement a user authentication system with the following features:
- JWT-based authentication
- Password hashing using bcrypt
- Refresh token mechanism
- Rate limiting for login attempts

[GitLab Duo]
I'll help you implement the authentication system. Here's the code...

[You]
/duo Add unit tests for the authentication system

[GitLab Duo]
Here are the unit tests for the authentication system...
```

### Best Practices

1. **One Task at a Time**
   - Use one Duo prompt for each specific task
   - Wait for Duo's response before sending the next prompt
   - Follow the sequence in the merge request template

2. **Clear Communication**
   - Keep prompts clear and specific
   - Include necessary context and requirements
   - Review Duo's response before proceeding

3. **Code Review**
   - Review generated code before committing
   - Test the implementation
   - Make necessary adjustments

4. **Progress Tracking**
   - Mark tasks as complete in the progress section
   - The agent will automatically track implementation progress
   - Update the acceptance criteria as you proceed

### Troubleshooting

If GitLab Duo doesn't respond:
1. Check if the prompt includes the `/duo` command
2. Ensure you're posting in the merge request discussion
3. Verify that GitLab Duo is enabled for your project
4. Try breaking down the prompt into smaller tasks


# Project setup
python3.12 -m venv venv
.\venv\Scripts\activate

python run.py SCRUM-198 123
python run.py SCRUM-198 70711629