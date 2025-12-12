# AIMA Application Status Checker

Automated service to check AIMA (Agência para a Integração, Migrações e Asilo) application status via web interface and Telegram bot.

## Features

- **Web Interface**: Simple form to check your AIMA application status instantly
- **Telegram Bot**: Interactive bot for credential setup and status monitoring
- **Periodic Checks**: Automatic hourly status checks with smart notifications
- **Secure Storage**: Credentials encrypted with per-user Fernet encryption
- **Scheduled Updates**: Daily status updates at 10 AM and 7 PM (Lisbon time)
- **Change Alerts**: Immediate notifications when your application status changes

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Web framework
- **python-telegram-bot** - Telegram integration
- **aiosqlite** - Async SQLite database
- **httpx** - Async HTTP client
- **BeautifulSoup4** - HTML parsing
- **cryptography** - Fernet encryption
- **APScheduler** - Task scheduling
- **Docker** - Containerization

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd EAIMA
   ```

2. Create `.env` file from example:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and set your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
   ```

4. Build and start the service:
   ```bash
   make build
   make up
   ```

5. Check logs to ensure everything is running:
   ```bash
   make logs
   ```

The web interface will be available at `http://localhost:8000`

## Usage

### Web Interface

1. Open `http://localhost:8000` in your browser
2. Enter your AIMA email and password
3. Click "Check Status"
4. View your current application status

### Telegram Bot

1. Start a chat with your bot on Telegram
2. Send `/start` command
3. Follow the prompts to enter your email and password
4. Choose whether to enable periodic checks
5. Receive status updates automatically

**Bot Commands:**
- `/start` - Set up credentials and enable monitoring
- `/status` - Check status immediately
- `/stop` - Disable periodic checks (keeps credentials)
- `/delete` - Completely delete all your data
- `/help` - Show help message with all commands
- `/cancel` - Cancel current operation

### Periodic Checks

When periodic checks are enabled:
- Status is checked every hour (distributed evenly across the hour)
- You receive immediate notification if status changes
- You receive scheduled updates at 10 AM and 7 PM Lisbon time
- Checks are sequential to avoid overloading AIMA servers

## Development

### Local Development

1. Install dependencies:
   ```bash
   make install
   ```

2. Run development server:
   ```bash
   make dev
   ```

The server will start with auto-reload enabled at `http://localhost:8000`

### Project Structure

```
EAIMA/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup
│   ├── crypto.py            # Encryption utilities
│   ├── aima_checker.py      # AIMA scraping logic
│   ├── services/
│   │   └── user_service.py  # User CRUD operations
│   ├── routers/
│   │   └── web.py           # Web endpoints
│   ├── telegram_bot/
│   │   ├── bot.py           # Bot initialization
│   │   ├── handlers.py      # Message handlers
│   │   └── scheduler.py     # Periodic checks
│   └── templates/
│       └── index.html       # Web UI
├── data/                    # SQLite database (created on first run)
├── pyproject.toml           # Poetry dependencies
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker Compose config
├── Makefile                 # Development commands
└── README.md                # This file
```

## Deployment

### Digital Ocean Droplet

1. Create a new droplet (Ubuntu 22.04 LTS recommended)

2. Install Docker and Docker Compose:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

3. Clone repository and configure:
   ```bash
   git clone <repository-url>
   cd EAIMA
   cp .env.example .env
   nano .env  # Edit with your bot token
   ```

4. Start the service:
   ```bash
   make build
   make up
   ```

5. (Optional) Set up nginx reverse proxy for HTTPS:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

6. Configure firewall:
   ```bash
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw allow 22/tcp
   ufw enable
   ```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (required) | - |
| `DATABASE_PATH` | SQLite database path | `./data/aima.db` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `AIMA_LOGIN_URL` | AIMA login page URL | `https://services.aima.gov.pt/RAR/login.php` |
| `AIMA_CHECK_URL` | AIMA login check endpoint | `https://services.aima.gov.pt/RAR/login_check3.php` |

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install dependencies with Poetry |
| `make dev` | Run development server with auto-reload |
| `make build` | Build Docker image |
| `make up` | Start services in background |
| `make down` | Stop services |
| `make logs` | View logs (follow mode) |
| `make shell` | Access container shell |
| `make restart` | Restart services |
| `make clean` | Remove containers, volumes, and database |
| `make status` | Show service status |
| `make help` | Show all available commands |

## Security

- **Encryption**: User credentials are encrypted using Fernet symmetric encryption
- **Per-User Keys**: Each user's data is encrypted with a unique key derived from bot token + user ID
- **No Plaintext Storage**: Passwords are never stored in plaintext
- **Secure Deletion**: Password messages are deleted from Telegram after processing
- **Data Control**: Users can delete all their data with `/delete` command
- **Auto-Cleanup**: Data is automatically deleted when users block/remove the bot
- **HTTPS**: Use reverse proxy for production deployment

## How It Works

### Status Checking

1. Fetch AIMA login page and extract CSRF token
2. Submit credentials with token to login endpoint
3. Parse response HTML for status table (salmon-colored background)
4. Extract and sanitize status text
5. Return formatted status or error message

### Scheduler Logic

- **Hourly Checks**: Spread evenly across the hour based on number of users
- **Jitter**: ±2 minutes random variation to avoid patterns
- **Sequential**: One user at a time to avoid simultaneous requests
- **Smart Notifications**:
  - Immediate if status changes
  - Scheduled at 10 AM & 7 PM if no change
  - Errors only reported at scheduled times

## Troubleshooting

### Bot not responding
- Check logs: `make logs`
- Verify bot token in `.env`
- Ensure container is running: `make status`

### Database errors
- Check permissions on `data/` directory
- Try clean restart: `make clean && make up`

### AIMA website timeout
- AIMA servers may be slow or under maintenance
- Retry after a few minutes
- Check if AIMA website is accessible in browser

### Health check failing
```bash
curl http://localhost:8000/health
```
Should return: `{"status": "ok"}`

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Disclaimer

This tool is for personal use only. It automates checking of publicly available information on the AIMA website. Users are responsible for:
- Securing their own credentials
- Complying with AIMA terms of service
- Not overloading AIMA servers

The developers are not affiliated with AIMA and provide this tool as-is without warranties.
