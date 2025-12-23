"""Web interface routes for FastAPI."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app import aima_checker
from app.constants import get_random_user_agent


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page with login form."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/check")
async def check_status(
    email: str = Form(...),
    password: str = Form(...)
):
    """
    Check AIMA application status.

    Args:
        email: User email
        password: User password

    Returns:
        JSONResponse: Status check result
    """
    # For web interface without user context, use a random user agent
    user_agent = get_random_user_agent()
    result = await aima_checker.login_and_get_status(email, password, user_agent)
    return JSONResponse(content=result)


@router.get("/health")
async def health_check():
    """Health check endpoint for Docker."""
    return {"status": "ok"}


@router.get("/config")
async def get_config():
    """Get current configuration (for debugging)."""
    from app.config import settings
    return {
        "log_level": settings.log_level,
        "database_path": settings.database_path,
        "aima_login_url": settings.aima_login_url,
        "aima_check_url": settings.aima_check_url,
        "verify_ssl": settings.verify_ssl
    }
