import time
import logging
from typing import Dict, List
import os
from pathlib import Path
from dotenv import load_dotenv
from jira_gitlab_agent import JiraGitlabAgent
import argparse

class StatusMonitor:
    """Monitor and update merge request status in real-time."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        # Setup logging
        self._setup_logging()
        
        # Load environment variables
        load_dotenv()
        
        # Initialize agent
        self.agent = JiraGitlabAgent(
            jira_url=os.getenv("JIRA_URL"),
            jira_username=os.getenv("JIRA_USERNAME"),
            jira_api_token=os.getenv("JIRA_API_TOKEN"),
            gitlab_url=os.getenv("GITLAB_URL"),
            gitlab_token=os.getenv("GITLAB_TOKEN"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            config_path=config_path
        )
        
        # Initialize tracking state
        self.active_mrs: Dict[str, Dict] = {}  # Store active MRs being monitored
        
    def _setup_logging(self):
        """Setup logging configuration."""
        log_file = "logs/status_monitor.log"
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def add_merge_request(self, project_id: int, mr_iid: int, issue_key: str):
        """Add a merge request to monitor."""
        mr_key = f"{project_id}:{mr_iid}"
        if mr_key not in self.active_mrs:
            self.active_mrs[mr_key] = {
                'project_id': project_id,
                'mr_iid': mr_iid,
                'issue_key': issue_key,
                'last_update': time.time()
            }
            self.logger.info(f"Started monitoring MR {mr_key} for issue {issue_key}")
    
    def remove_merge_request(self, project_id: int, mr_iid: int):
        """Remove a merge request from monitoring."""
        mr_key = f"{project_id}:{mr_iid}"
        if mr_key in self.active_mrs:
            del self.active_mrs[mr_key]
            self.logger.info(f"Stopped monitoring MR {mr_key}")
    
    def update_merge_request_status(self, project_id: int, mr_iid: int) -> Dict:
        """Update status for a single merge request."""
        try:
            # Update progress through the agent
            progress = self.agent.update_merge_request_progress(project_id, mr_iid)
            
            # Get the MR object
            project = self.agent.gitlab.projects.get(project_id)
            mr = project.mergerequests.get(mr_iid)
            
            # Check if MR is closed or merged
            if mr.state in ['merged', 'closed']:
                self.remove_merge_request(project_id, mr_iid)
                
            return progress
        except Exception as e:
            self.logger.error(f"Error updating MR {project_id}:{mr_iid}: {str(e)}")
            return {}
    
    def update_jira_status(self, issue_key: str, progress: Dict):
        """Update Jira status based on MR progress."""
        try:
            # Define status mapping based on progress
            if progress.get('acceptance', False):
                new_status = 'done'
            elif progress.get('review', False):
                new_status = 'in_review'
            elif any([progress.get(key, False) for key in ['implementation', 'tests', 'documentation']]):
                new_status = 'in_progress'
            else:
                new_status = 'to_do'
            
            # Update Jira status
            self.agent.update_jira_status(issue_key, new_status)
            
        except Exception as e:
            self.logger.error(f"Error updating Jira status for {issue_key}: {str(e)}")
    
    def monitor_loop(self, update_interval: int = 300):
        """Main monitoring loop."""
        self.logger.info("Starting status monitor loop")
        
        try:
            while True:
                current_time = time.time()
                
                # Update each active merge request
                for mr_key, mr_info in list(self.active_mrs.items()):
                    # Check if it's time to update this MR
                    if current_time - mr_info['last_update'] >= update_interval:
                        self.logger.info(f"Updating status for MR {mr_key}")
                        
                        # Update progress
                        progress = self.update_merge_request_status(
                            mr_info['project_id'],
                            mr_info['mr_iid']
                        )
                        
                        # Update Jira status
                        if progress:
                            self.update_jira_status(mr_info['issue_key'], progress)
                            
                        # Update last update time
                        mr_info['last_update'] = current_time
                
                # Sleep for a short interval
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            self.logger.info("Status monitor stopped by user")
        except Exception as e:
            self.logger.error(f"Error in monitor loop: {str(e)}")
            raise

def main():
    """Main entry point for the status monitor."""
    parser = argparse.ArgumentParser(description='Monitor merge request status')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    parser.add_argument('--interval', type=int, default=300, help='Update interval in seconds')
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = StatusMonitor(config_path=args.config)
    
    # Start monitoring loop
    monitor.monitor_loop(update_interval=args.interval)

if __name__ == "__main__":
    main() 