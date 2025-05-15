document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('repo-form');
    const loading = document.getElementById('loading');
    const commitsContainer = document.getElementById('commits-container');
    const filterSection = document.getElementById('filter-section');
    const shareButton = document.getElementById('share-button');
    const shareModal = document.getElementById('share-modal');
    const modalClose = document.querySelector('.modal-close');
    const copyButton = document.getElementById('copy-button');
    const shareUrl = document.getElementById('share-url');
    const themeSwitch = document.querySelector('.theme-switch');
    const progressStatus = document.getElementById('progress-status');
    const progressDetail = document.getElementById('progress-detail');
    const progressBar = document.getElementById('progress-bar');
    const githubAuthBtn = document.getElementById('github-auth');
    const authStatus = document.getElementById('auth-status');

    // Configuration
    const API_PORTS = [5001, 5002, 5003, 5004, 5005];
    let API_BASE_URL = null;

    // GitHub authentication state
    let githubToken = localStorage.getItem('github_token');
    let githubUsername = localStorage.getItem('github_username');

    // Update auth button state
    function updateAuthState() {
        if (githubToken && githubUsername) {
            githubAuthBtn.classList.add('authenticated');
            githubAuthBtn.innerHTML = `<i class="fab fa-github"></i>Connected as ${githubUsername}`;
            authStatus.classList.add('authenticated');
            authStatus.innerHTML = '<i class="fas fa-check-circle"></i>Ready to analyze private repositories';
        } else {
            githubAuthBtn.classList.remove('authenticated');
            githubAuthBtn.innerHTML = '<i class="fab fa-github"></i>Connect GitHub';
            authStatus.classList.remove('authenticated');
            authStatus.innerHTML = '<i class="fas fa-info-circle"></i>Connect to analyze private repositories';
        }
    }

    // Initialize auth state
    updateAuthState();

    // Handle GitHub authentication
    githubAuthBtn.addEventListener('click', () => {
        if (githubToken) {
            // Logout
            localStorage.removeItem('github_token');
            localStorage.removeItem('github_username');
            githubToken = null;
            githubUsername = null;
            updateAuthState();
        } else {
            // Login - Get client ID from backend
            fetch(`${API_BASE_URL}/auth/config`)
                .then(response => response.json())
                .then(data => {
                    if (data.client_id) {
                        const state = Math.random().toString(36).substring(7);
                        localStorage.setItem('oauth_state', state);
                        const authUrl = `https://github.com/login/oauth/authorize?client_id=${data.client_id}&redirect_uri=${encodeURIComponent(window.location.origin + '/callback')}&scope=repo&state=${state}`;
                        window.location.href = authUrl;
                    } else {
                        authStatus.classList.add('error');
                        authStatus.innerHTML = '<i class="fas fa-exclamation-circle"></i>GitHub authentication not configured';
                    }
                })
                .catch(error => {
                    console.error('Failed to get auth config:', error);
                    authStatus.classList.add('error');
                    authStatus.innerHTML = '<i class="fas fa-exclamation-circle"></i>Authentication not available';
                });
        }
    });

    // Handle OAuth callback
    if (window.location.pathname === '/callback') {
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const state = params.get('state');
        const savedState = localStorage.getItem('oauth_state');

        if (state === savedState) {
            localStorage.removeItem('oauth_state');
            fetch(`${API_BASE_URL}/auth/callback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ code }),
            })
                .then(response => response.json())
                .then(data => {
                    if (data.access_token) {
                        localStorage.setItem('github_token', data.access_token);
                        localStorage.setItem('github_username', data.username);
                        window.location.href = '/';
                    } else {
                        console.error('Failed to get access token:', data.error);
                        authStatus.classList.add('error');
                        authStatus.innerHTML = '<i class="fas fa-exclamation-circle"></i>Authentication failed';
                    }
                })
                .catch(error => {
                    console.error('Auth error:', error);
                    authStatus.classList.add('error');
                    authStatus.innerHTML = '<i class="fas fa-exclamation-circle"></i>Authentication failed';
                });
        } else {
            console.error('Invalid state parameter');
            authStatus.classList.add('error');
            authStatus.innerHTML = '<i class="fas fa-exclamation-circle"></i>Invalid authentication state';
        }
    }

    // Find active API endpoint
    async function findActiveEndpoint() {
        const progressStatus = document.getElementById('progress-status');
        const progressDetail = document.getElementById('progress-detail');

        for (const port of API_PORTS) {
            try {
                progressDetail.textContent = `Trying to connect to port ${port}...`;
                const response = await fetch(`http://localhost:${port}/health`);
                if (response.ok) {
                    API_BASE_URL = `http://localhost:${port}`;
                    return true;
                }
            } catch (error) {
                console.log(`Port ${port} not available`);
            }
        }
        progressStatus.textContent = 'Connection Error';
        progressDetail.textContent = 'Could not connect to the backend server. Please make sure it is running.';
        return false;
    }

    // Theme Switching
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    themeSwitch.innerHTML = `<i class="fas fa-${theme === 'light' ? 'sun' : 'moon'}"></i>`;

    themeSwitch.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        themeSwitch.innerHTML = `<i class="fas fa-${newTheme === 'light' ? 'sun' : 'moon'}"></i>`;
    });

    // Filter Functionality
    const authorFilter = document.getElementById('author-filter');
    const dateFilter = document.getElementById('date-filter');
    const searchFilter = document.getElementById('search-filter');

    function filterCommits() {
        const author = authorFilter.value.toLowerCase();
        const date = dateFilter.value;
        const search = searchFilter.value.toLowerCase();

        const filteredCommits = currentCommits.filter(commit => {
            const matchesAuthor = !author || commit.author.toLowerCase().includes(author);
            const matchesSearch = !search ||
                commit.message.toLowerCase().includes(search) ||
                commit.explanation.toLowerCase().includes(search);

            let matchesDate = true;
            if (date !== 'all') {
                const commitDate = new Date(commit.date);
                const now = new Date();
                const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                const thisWeek = new Date(today);
                thisWeek.setDate(today.getDate() - 7);
                const thisMonth = new Date(now.getFullYear(), now.getMonth(), 1);

                switch (date) {
                    case 'today':
                        matchesDate = commitDate >= today;
                        break;
                    case 'week':
                        matchesDate = commitDate >= thisWeek;
                        break;
                    case 'month':
                        matchesDate = commitDate >= thisMonth;
                        break;
                }
            }

            return matchesAuthor && matchesSearch && matchesDate;
        });

        displayCommits(filteredCommits);
    }

    authorFilter.addEventListener('input', filterCommits);
    dateFilter.addEventListener('change', filterCommits);
    searchFilter.addEventListener('input', filterCommits);

    function displayCommits(commits, isNewAnalysis = false) {
        if (isNewAnalysis) {
            currentCommits = commits;
        }

        commitsContainer.innerHTML = '';
        const template = document.getElementById('commit-template');

        commits.forEach(commit => {
            const commitElement = template.content.cloneNode(true);

            commitElement.querySelector('.commit-title').textContent = commit.message;
            commitElement.querySelector('.commit-author').textContent = commit.author;
            commitElement.querySelector('.commit-date').textContent = new Date(commit.date).toLocaleDateString();
            commitElement.querySelector('.commit-hash span').textContent = commit.hash.substring(0, 7);
            commitElement.querySelector('.commit-explanation').textContent = commit.explanation;

            commitsContainer.appendChild(commitElement);
        });

        if (commits.length === 0) {
            commitsContainer.innerHTML = '<div class="no-results">No commits match the current filters</div>';
        }
    }

    function updateProgress(status, detail, progress) {
        progressStatus.textContent = status;
        progressDetail.textContent = detail;
        progressBar.style.width = `${progress}%`;
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const repoUrl = document.getElementById('repo-url').value.trim();
        if (!repoUrl) return;

        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.classList.add('loading');
        submitButton.disabled = true;

        // Reset filters
        authorFilter.value = '';
        dateFilter.value = 'all';
        searchFilter.value = '';

        // Show loading state
        filterSection.style.display = 'none';
        loading.style.display = 'block';
        commitsContainer.innerHTML = '';
        shareButton.style.display = 'none';

        try {
            if (!API_BASE_URL && !(await findActiveEndpoint())) {
                throw new Error('No active API endpoint found');
            }

            updateProgress('Analyzing repository...', 'This may take a few minutes', 0);

            const response = await fetch(`${API_BASE_URL}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(githubToken && { 'Authorization': `Bearer ${githubToken}` })
                },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    github_token: githubToken
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to analyze repository');
            }

            const data = await response.json();
            if (data.errors && data.errors.length > 0) {
                console.warn('Some commits could not be analyzed:', data.errors);
            }

            displayCommits(data.commits, true);
            filterSection.style.display = 'block';
            shareButton.style.display = 'block';
        } catch (error) {
            console.error('Error:', error);
            commitsContainer.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>${error.message}</p>
                </div>
            `;
        } finally {
            submitButton.classList.remove('loading');
            submitButton.disabled = false;
            loading.style.display = 'none';
        }
    });

    // Share functionality
    shareButton.addEventListener('click', () => {
        shareModal.classList.add('active');
        const shareData = {
            repo_url: document.getElementById('repo-url').value,
            filters: {
                author: authorFilter.value,
                date: dateFilter.value,
                search: searchFilter.value
            }
        };
        const shareString = btoa(encodeURIComponent(JSON.stringify(shareData)));
        shareUrl.value = `${window.location.origin}${window.location.pathname}?share=${shareString}`;
    });

    modalClose.addEventListener('click', () => {
        shareModal.classList.remove('active');
    });

    shareModal.addEventListener('click', (e) => {
        if (e.target === shareModal) {
            shareModal.classList.remove('active');
        }
    });

    shareModal.querySelector('.modal-content').addEventListener('click', (e) => {
        e.stopPropagation();
    });

    copyButton.addEventListener('click', () => {
        shareUrl.select();
        document.execCommand('copy');
        copyButton.innerHTML = '<i class="fas fa-check"></i>Copied';
        setTimeout(() => {
            copyButton.innerHTML = '<i class="fas fa-copy"></i>Copy';
        }, 2000);
    });

    // Handle shared links
    const urlParams = new URLSearchParams(window.location.search);
    const sharedData = urlParams.get('share');

    if (sharedData) {
        try {
            const data = JSON.parse(decodeURIComponent(atob(sharedData)));
            document.getElementById('repo-url').value = data.repo_url;
            authorFilter.value = data.filters.author || '';
            dateFilter.value = data.filters.date || 'all';
            searchFilter.value = data.filters.search || '';
            form.dispatchEvent(new Event('submit'));
        } catch (error) {
            console.error('Error loading shared data:', error);
        }
    }

    // Export functionality
    document.querySelectorAll('.export-button').forEach(button => {
        button.addEventListener('click', () => {
            const format = button.dataset.format;
            if (!currentCommits || currentCommits.length === 0) {
                alert('No data to export');
                return;
            }

            if (format === 'json') {
                const dataStr = JSON.stringify(currentCommits, null, 2);
                const blob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'commit-analysis.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } else if (format === 'pdf') {
                alert('PDF export is not implemented in the local version');
            }
        });
    });
});