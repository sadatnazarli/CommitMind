import os
import shutil
from git import Repo, GitCommandError, InvalidGitRepositoryError
from git.exc import GitError
from typing import List, Dict, Optional
import tempfile
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitError(Exception):
    """Custom exception for Git-related errors"""
    pass

class GitParser:
    def __init__(self, temp_dir: str = "../temp"):
        """Initialize GitParser with a temporary directory"""
        self.temp_dir = os.path.abspath(temp_dir)
        try:
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            # Test if directory is writable
            test_file = os.path.join(temp_dir, '.test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            raise GitError(f"Failed to initialize temporary directory: {str(e)}")

    def _sanitize_repo_name(self, repo_url: str) -> str:
        """Sanitize repository name to prevent path traversal"""
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        # Remove any potentially dangerous characters
        repo_name = re.sub(r'[^a-zA-Z0-9_-]', '_', repo_name)
        return repo_name

    def _create_temp_dir(self) -> str:
        """Create a unique temporary directory"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_dir = os.path.join(self.temp_dir, f"repo_{timestamp}_{os.getpid()}")
        os.makedirs(unique_dir, exist_ok=True)
        return unique_dir

    def clone_repo(self, repo_url: str, github_token: Optional[str] = None) -> str:
        """Clone a repository and return its path with improved error handling"""
        if not isinstance(repo_url, str) or not repo_url.strip():
            raise ValueError("Repository URL must be a non-empty string")

        repo_name = self._sanitize_repo_name(repo_url)
        repo_path = os.path.join(self._create_temp_dir(), repo_name)

        logger.info(f"Cloning repository from {repo_url} to {repo_path}")

        try:
            # Clean up existing repo if it exists
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)

            # Modify URL to include token if provided
            clone_url = repo_url
            if github_token:
                # Extract the repository path
                if repo_url.startswith('https://github.com/'):
                    clone_url = f'https://{github_token}@github.com/{repo_url[19:]}'

            # Clone with progress
            repo = Repo.clone_from(
                clone_url,
                repo_path,
                depth=50,  # Limit history for faster cloning
                no_single_branch=True  # Fetch all branches
            )
            return repo_path

        except GitCommandError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                raise GitError(f"Repository not found: {repo_url}")
            elif "authentication" in error_msg.lower():
                raise GitError(f"Authentication failed for repository: {repo_url}")
            else:
                raise GitError(f"Failed to clone repository: {error_msg}")
        except Exception as e:
            raise GitError(f"Unexpected error while cloning repository: {str(e)}")

    def get_recent_commits(self, repo_path: str, num_commits: int = 10) -> List[Dict]:
        """Get information about recent commits with improved error handling"""
        if not isinstance(repo_path, str) or not os.path.exists(repo_path):
            raise ValueError("Invalid repository path")
        if not isinstance(num_commits, int) or num_commits <= 0:
            raise ValueError("Number of commits must be a positive integer")

        try:
            repo = Repo(repo_path)
        except (InvalidGitRepositoryError, GitError) as e:
            raise GitError(f"Invalid Git repository: {str(e)}")

        try:
            # Determine the default branch with better error handling
            default_branch = self._get_default_branch(repo)
            logger.info(f"Using default branch: {default_branch}")

            commits = []
            for commit in repo.iter_commits(default_branch, max_count=num_commits):
                try:
                    # Get the diff with better error handling
                    diff = self._get_commit_diff(repo, commit)

                    commits.append({
                        'hash': commit.hexsha,
                        'message': commit.message.strip(),
                        'author': f"{commit.author.name} <{commit.author.email}>",
                        'date': commit.committed_datetime.isoformat(),
                        'diff': diff,
                        'branch': default_branch
                    })
                except Exception as e:
                    logger.warning(f"Error processing commit {commit.hexsha}: {str(e)}")
                    # Continue with next commit instead of failing entirely
                    continue

            return commits

        except Exception as e:
            raise GitError(f"Failed to get commits: {str(e)}")

    def _get_default_branch(self, repo: Repo) -> str:
        """Determine the default branch of the repository"""
        try:
            # Try to get the default branch from remote
            default_branch = repo.active_branch.name
            return default_branch
        except Exception:
            # If active branch detection fails, try common branch names
            for branch in ['main', 'master', 'HEAD']:
                try:
                    list(repo.iter_commits(branch, max_count=1))
                    return branch
                except Exception:
                    continue
            raise GitError("Could not determine default branch")

    def _get_commit_diff(self, repo: Repo, commit) -> str:
        """Get the diff for a commit with proper error handling"""
        try:
            if commit.parents:
                return repo.git.diff(commit.parents[0].hexsha, commit.hexsha)
            else:
                # For initial commit
                return repo.git.show('--pretty=format:', '--patch', commit.hexsha)
        except Exception as e:
            logger.warning(f"Failed to get diff for commit {commit.hexsha}: {str(e)}")
            return "Error: Could not retrieve diff"

    def cleanup(self):
        """Clean up temporary directory with improved error handling"""
        if not os.path.exists(self.temp_dir):
            return

        try:
            # Remove read-only attributes if they exist
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    try:
                        os.chmod(os.path.join(root, name), 0o666)
                    except:
                        pass
                for name in dirs:
                    try:
                        os.chmod(os.path.join(root, name), 0o777)
                    except:
                        pass

            shutil.rmtree(self.temp_dir, ignore_errors=True)
            os.makedirs(self.temp_dir, exist_ok=True)
            logger.info("Successfully cleaned up temporary directory")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            # Don't raise the error as this is a cleanup operation