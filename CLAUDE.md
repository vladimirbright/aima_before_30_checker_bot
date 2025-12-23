# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIMA Application Status Checker - Automated service to check AIMA (Agência para a Integração, Migrações e Asilo) application status via web interface and Telegram bot. The system scrapes the AIMA website, stores encrypted credentials, and provides periodic status monitoring with smart notifications.

**Tech Stack:** Python 3.13+, FastAPI, python-telegram-bot, aiosqlite, httpx, BeautifulSoup4, cryptography, APScheduler

## Development Commands

### Local Development
```bash
make install           # Install dependencies with Poetry
make dev              # Run development server with auto-reload (http://localhost:8000)
poetry run pytest     # Run tests
```

### Docker Operations
```bash
make build            # Build Docker image
make up               # Start services in background
make down             # Stop services
make logs             # View logs (follow mode)
make shell            # Access container shell
make restart          # Restart services
make clean            # Remove containers, volumes, and database
make status           # Show service status
```

### Setup
1. Copy `.env.example` to `.env`
2. Set `TELEGRAM_BOT_TOKEN` in `.env` (required)
3. Run `make build && make up`

## Architecture

### Application Lifecycle (app/main.py)
The FastAPI application uses a lifespan context manager that coordinates startup/shutdown:
1. **Startup**: Database initialization → Telegram bot creation → Bot start → Scheduler start
2. **Shutdown**: Scheduler stop → Bot stop → Database cleanup

Both the Telegram bot and web interface run concurrently in the same FastAPI process.

### Core Components

**AIMA Scraper (app/aima_checker.py)**
- Fetches login page and extracts CSRF token from hidden input
- Submits credentials with token to login endpoint
- Handles JavaScript redirects (looks for `window.location.href` in response)
- Parses HTML to find status in salmon-colored table cell (`<td style="background-color: salmon;">`)
- Status text is extracted from `<ul>` tag and sanitized
- Saves response HTML to `/tmp/aima_response.html` for debugging
- **Proxy support**: If `PROXY_URL` is configured, all requests route through the specified proxy

**Encryption (app/crypto.py)**
- Per-user encryption using Fernet symmetric encryption
- Encryption key derived from HMAC-SHA256(bot_token, user_id)
- Credentials stored encrypted in database, never in plaintext

**Scheduler (app/telegram_bot/scheduler.py)**
- **Hourly checks**: Distributed evenly across users (50-minute window with ±2min jitter)
- **Scheduled notifications**: 10 AM and 7 PM Lisbon time
- **Smart notifications**:
  - Immediate notification if status changes
  - Scheduled updates at 10 AM/7 PM if no change
  - Errors only reported during scheduled times
- Users processed sequentially to avoid overloading AIMA servers

**Database (app/database.py)**
- SQLite with aiosqlite for async operations
- Schema: users table with encrypted credentials, status tracking, periodic check flag
- Per-operation connection management (no persistent pool)

### Configuration (app/config.py)
Settings loaded from environment variables using pydantic-settings:
- `TELEGRAM_BOT_TOKEN` (required)
- `DATABASE_PATH` (default: `./data/aima.db`)
- `LOG_LEVEL` (default: `INFO`)
- `AIMA_LOGIN_URL` and `AIMA_CHECK_URL` (AIMA endpoints)
- `VERIFY_SSL` (default: `False` - AIMA has certificate issues)
- `PROXY_URL` (optional) - HTTP/HTTPS proxy URL in format `http://user:pass@host:port`
  - If configured, all AIMA requests will route through this proxy
  - Credentials are masked in logs for security
  - Leave empty/unset to use direct connection

### Project Structure
```
app/
├── main.py                     # FastAPI app with lifespan manager
├── config.py                   # Settings from environment
├── database.py                 # aiosqlite connection and schema
├── crypto.py                   # Fernet encryption utilities
├── aima_checker.py            # Web scraping logic for AIMA
├── utils.py                    # Timestamp formatting
├── services/
│   └── user_service.py        # User CRUD operations
├── routers/
│   └── web.py                 # Web interface endpoints
├── telegram_bot/
│   ├── bot.py                 # Bot initialization
│   ├── handlers.py            # Command and message handlers
│   └── scheduler.py           # Periodic checks and notifications
└── templates/
    └── index.html             # Web UI template

data/                          # SQLite database (created on first run)
```

## Important Notes

### AIMA Scraping Specifics
- AIMA uses CSRF tokens in login forms (hidden input `name="tok"`)
- Login success is detected by checking if response redirects to `login.php` (failure) or contains JavaScript redirect (success)
- JavaScript redirects are in format: `window.location.href="/RAR/2fase/sumario.php"`
- Status is always in a table cell with `background-color: salmon` style
- The actual status text is in a `<ul>` element inside that cell

### Scheduler Behavior
- Hourly checks spread users across 50 minutes (not 60) to leave buffer
- Random ±2 minute jitter prevents predictable patterns
- Sequential processing (one user at a time) prevents simultaneous AIMA requests
- First check of the hour starts immediately, subsequent checks are delayed

### Security
- Each user's data encrypted with unique key from bot token + user ID
- Password messages deleted from Telegram after processing
- Users can delete all data with `/delete` command
- Data auto-cleaned when users block/remove bot

### Health Check
Available at `/health` endpoint - returns `{"status": "ok"}`

### Timezone
All scheduler operations use Europe/Lisbon timezone via pytz
