from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from git_parser import GitParser
from ai_explainer import AIExplainer
import os
import traceback
import socket
from typing import Optional, List, Dict, Tuple
from urllib.parse import urlparse
import re
import requests
from dotenv import load_dotenv
import atexit

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Rate limiting configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per day", "10 per hour"]
)

# Configuration
DEFAULT_PORT = 5001
MAX_PORT_ATTEMPTS = 10
MAX_COMMITS = 20  # Maximum number of commits to analyze
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')

if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
    print("Warning: GitHub OAuth credentials not configured. Private repository analysis will be disabled.")

git_parser = GitParser()
ai_explainer = AIExplainer()

# Register cleanup on application shutdown
@atexit.register
def cleanup_on_exit():
    """Clean up temporary files on application shutdown"""
    try:
        git_parser.cleanup()
    except Exception as e:
        print(f"Error during cleanup: {e}")

def validate_github_url(url: str) -> Tuple[bool, str]:
    """
    Validate if the URL is a valid GitHub repository URL
    Returns: (is_valid, error_message)
    """
    if not url:
        return False, "Repository URL is required"

    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in ('http', 'https'):
            return False, "URL must start with http:// or https://"

        # Check domain
        if parsed.netloc not in ('github.com', 'www.github.com'):
            return False, "URL must be from github.com"

        # Check path format
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) < 2:
            return False, "URL must include username and repository name"

        # Check for valid GitHub username and repo name format
        username, repo = path_parts[:2]
        username_pattern = r'^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$'
        repo_pattern = r'^[a-zA-Z0-9_.-]+$'

        if not re.match(username_pattern, username):
            return False, "Invalid GitHub username format"

        if not re.match(repo_pattern, repo):
            return False, "Invalid repository name format"

        # Check for common mistakes
        if parsed.path.endswith('.git'):
            return False, "Please remove .git from the end of the URL"

        if len(path_parts) > 2 and path_parts[2] in ['tree', 'blob', 'commits']:
            return False, "Please provide the main repository URL, not a specific branch or file"

        return True, ""

    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"

def find_available_port(start_port: int, max_attempts: int) -> Optional[int]:
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except socket.error:
            continue
    return None

def format_error_response(error: str, status_code: int = 500) -> tuple:
    """Format error response with consistent structure"""
    return jsonify({
        'success': False,
        'error': error,
        'status_code': status_code
    }), status_code

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'CommitMind API',
        'version': '1.0.0'
    })

@app.route('/analyze', methods=['POST'])
@limiter.limit("5 per minute")  # Rate limit for analysis endpoint
def analyze_repo():
    try:
        data = request.get_json()
        if not data:
            return format_error_response('Request body is required', 400)

        repo_url = data.get('repo_url', '').strip()
        github_token = data.get('github_token')

        # Validate GitHub URL
        is_valid, error_message = validate_github_url(repo_url)
        if not is_valid:
            return format_error_response(error_message, 400)

        print(f"Cloning repository: {repo_url}")
        try:
            # Pass GitHub token to clone_repo
            repo_path = git_parser.clone_repo(repo_url, github_token)
        except GitError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                return format_error_response("Repository not found. Please check if the URL is correct and the repository exists.", 404)
            elif "permission denied" in error_msg.lower() or "authentication" in error_msg.lower():
                return format_error_response("Access denied. Please make sure you have access to this repository and are properly authenticated.", 403)
            else:
                return format_error_response(f'Failed to clone repository: {error_msg}', 400)
        except Exception as e:
            return format_error_response(f'Failed to clone repository: {str(e)}', 500)

        print("Getting recent commits...")
        try:
            commits = git_parser.get_recent_commits(repo_path)[:MAX_COMMITS]
            print(f"Found {len(commits)} commits")

            if not commits:
                return format_error_response('No commits found in the repository', 404)

        except Exception as e:
            return format_error_response(f'Failed to fetch commits: {str(e)}', 500)

        print("Generating explanations...")
        explained_commits = []
        errors = []

        for i, commit in enumerate(commits):
            print(f"Processing commit {i+1}/{len(commits)}: {commit['hash'][:7]}")
            try:
                explanation = ai_explainer.explain_commit(commit)
                if explanation.startswith('Error:'):
                    errors.append(explanation)
                explained_commits.append({
                    'hash': commit['hash'],
                    'message': commit['message'],
                    'author': commit['author'],
                    'date': commit['date'],
                    'explanation': explanation
                })
            except Exception as e:
                error_msg = str(e)
                print(f"Error explaining commit {commit['hash'][:7]}: {error_msg}")
                print(traceback.format_exc())
                errors.append(f"Failed to explain commit {commit['hash']}: {error_msg}")
                explained_commits.append({
                    'hash': commit['hash'],
                    'message': commit['message'],
                    'author': commit['author'],
                    'date': commit['date'],
                    'explanation': 'Error generating explanation',
                    'status': 'error',
                    'error': error_msg
                })

        print("Cleaning up...")
        git_parser.cleanup()

        print("Done! Sending response...")
        return jsonify({
            'success': True,
            'commits': explained_commits,
            'total_commits': len(commits),
            'successful_commits': len([c for c in explained_commits if c['status'] == 'success']),
            'failed_commits': len(errors),
            'errors': errors if errors else None
        })

    except Exception as e:
        print(f"Error in analyze_repo: {str(e)}")
        print(traceback.format_exc())
        return format_error_response(f'Internal server error: {str(e)}', 500)
    finally:
        # Ensure cleanup happens even if an error occurs
        try:
            git_parser.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {e}")

@app.route('/auth/callback', methods=['POST'])
@limiter.limit("10 per minute")  # Rate limit for auth callback
def github_callback():
    """Handle GitHub OAuth callback"""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return format_error_response('GitHub OAuth is not configured', 501)

    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return format_error_response('Authorization code is required', 400)

        code = data['code']

        # Exchange code for access token
        response = requests.post(
            'https://github.com/login/oauth/access_token',
            headers={'Accept': 'application/json'},
            data={
                'client_id': GITHUB_CLIENT_ID,
                'client_secret': GITHUB_CLIENT_SECRET,
                'code': code
            }
        )

        if not response.ok:
            return format_error_response('Failed to exchange code for token', 400)

        token_data = response.json()
        if 'error' in token_data:
            return format_error_response(f"GitHub OAuth error: {token_data['error']}", 400)

        access_token = token_data.get('access_token')
        if not access_token:
            return format_error_response('No access token received', 400)

        # Get user information
        user_response = requests.get(
            'https://api.github.com/user',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
        )

        if not user_response.ok:
            return format_error_response('Failed to get user information', 400)

        user_data = user_response.json()
        username = user_data.get('login')

        return jsonify({
            'success': True,
            'access_token': access_token,
            'username': username
        })

    except Exception as e:
        print(f"Error in github_callback: {str(e)}")
        print(traceback.format_exc())
        return format_error_response(f'Internal server error: {str(e)}', 500)

def run_app():
    """Run the Flask app with automatic port selection"""
    port = find_available_port(DEFAULT_PORT, MAX_PORT_ATTEMPTS)
    if port is None:
        print(f"Could not find an available port in range {DEFAULT_PORT}-{DEFAULT_PORT + MAX_PORT_ATTEMPTS - 1}")
        return

    print(f"Starting server on port {port}")
    app.run(debug=True, port=port)

if __name__ == '__main__':
    run_app()