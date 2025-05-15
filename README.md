# CommitMind

<div align="center">
  <img src="./logoofcommitming.png" alt="CommitMind Logo" width="400"/>
  <h3>AI-Powered Git Commit Analysis Tool</h3>
  <p>Understand your project's history through intelligent commit analysis</p>
</div>

---

## Overview

CommitMind is a powerful web application that leverages artificial intelligence to analyze Git repositories. It provides detailed explanations for commit changes, helping developers and teams better understand their project's evolution and development patterns.

## Features

- **Repository Analysis**
  - Support for public GitHub repositories
  - Private repository access with GitHub OAuth
  - Intelligent commit explanation generation
  - Detailed change analysis

- **Advanced Filtering**
  - Filter by author
  - Filter by date range
  - Full-text search in commits
  - Real-time results updating

- **User Experience**
  - Dark/Light theme with persistence
  - Modern glassmorphism design
  - Responsive layout for all devices
  - Share analysis via URL

## Local Setup

### Prerequisites

- Python 3.8 or higher
- Node.js
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/sadatnazarli/CommitMind.git
cd CommitMind
```

2. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Configure environment variables:
   - Create a `.env` file in the backend directory
   - Add the following configuration:
   ```
   # Required for private repository access
   GITHUB_CLIENT_ID=your_github_client_id
   GITHUB_CLIENT_SECRET=your_github_client_secret
   ```

### Running the Application

1. Start the backend server:
```bash
# From the backend directory
python app.py
```
The server will automatically find an available port between 5001-5005.

2. Start the frontend server:
```bash
# From the frontend directory
cd ../frontend
python -m http.server 8000
```

3. Access the application:
```
http://localhost:8000
```

## GitHub OAuth Configuration

For private repository access:

1. Go to GitHub Settings > Developer Settings > OAuth Apps
2. Create a new OAuth App with:
   - Application name: `CommitMind Local`
   - Homepage URL: `http://localhost:8000`
   - Authorization callback URL: `http://localhost:8000/callback`
3. Copy the Client ID and Client Secret to your `.env` file

## Usage Guide

1. Repository URL Format:
   ```
   https://github.com/username/repository
   ```

2. Authentication:
   - Click "Connect GitHub" for private repositories
   - Wait for authentication confirmation

3. Analysis:
   - Enter repository URL
   - Click "Analyze Repository"
   - Wait for the analysis to complete

4. Exploring Results:
   - Use author filter for specific contributors
   - Select date range for time-based analysis
   - Search through commit messages and explanations
   - Share results using the share button

## Technical Details

- Maximum analysis limit: 20 most recent commits
- Rate limiting:
  - 100 requests per day
  - 10 requests per hour
  - 5 analysis requests per minute

## Security Notes

- GitHub tokens are stored securely in local storage
- Environment variables are used for sensitive data
- CORS protection is enabled
- Rate limiting prevents abuse

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p>Built for developers who value understanding their code's history</p>
</div>