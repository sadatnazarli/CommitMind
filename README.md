# CommitMind

<p align="center">
  <img src="logo.png" alt="CommitMind Logo" width="200"/>
</p>

<p align="center">
  🧠 AI-Powered Git Commit Analysis Tool
</p>

CommitMind is a powerful web application that uses AI to analyze Git repositories, providing insightful explanations for commit changes and helping developers better understand project history.

## ✨ Features

- 🔍 Analyze any public GitHub repository
- 🔐 Support for private repositories with GitHub OAuth
- 🌙 Dark/Light theme with persistence
- 🔍 Advanced commit filtering by:
  - Author
  - Date range
  - Search terms
- 📤 Share analysis results via URL
- 📱 Responsive design for all devices
- 🎨 Modern glassmorphism UI

## 🚀 Local Setup

### Prerequisites

- Python 3.8 or higher
- Node.js (for running the frontend server)
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CommitMind.git
cd CommitMind
```

2. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Create a `.env` file in the backend directory:
```bash
# Required for private repository access
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

### Running the Application

1. Start the backend server (from the backend directory):
```bash
python app.py
```
The server will automatically find an available port between 5001-5005.

2. Start the frontend server (from the frontend directory):
```bash
cd ../frontend
python -m http.server 8000
```

3. Open your browser and visit:
```
http://localhost:8000
```

## 🔒 GitHub OAuth Setup (Optional)

Only required if you want to analyze private repositories:

1. Go to GitHub Settings > Developer Settings > OAuth Apps
2. Click "New OAuth App"
3. Fill in the following:
   - Application name: CommitMind Local
   - Homepage URL: http://localhost:8000
   - Authorization callback URL: http://localhost:8000/callback
4. Copy the Client ID and Client Secret to your `.env` file

## 🛠️ Usage

1. Enter a GitHub repository URL in the format:
   ```
   https://github.com/username/repository
   ```

2. If analyzing private repositories, click "Connect GitHub" to authenticate

3. Wait for the analysis to complete

4. Use the filters to explore commits:
   - Filter by author name
   - Select date range (Today, This Week, This Month)
   - Search commit messages and explanations

5. Share your analysis by clicking the "Share" button

## ⚠️ Limitations

- Maximum of 20 most recent commits are analyzed per request
- Repository URL must be in the correct GitHub format
- Private repositories require GitHub authentication
- The application is designed for local use only

## 🤝 Contributing

This is a local development tool. Feel free to fork and modify for your needs.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<p align="center">
Made with ❤️ for developers who want to understand code better
</p>