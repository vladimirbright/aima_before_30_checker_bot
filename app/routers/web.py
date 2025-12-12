"""Web interface routes for FastAPI."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app import aima_checker


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
    result = await aima_checker.login_and_get_status(email, password)
    return JSONResponse(content=result)


@router.get("/health")
async def health_check():
    """Health check endpoint for Docker."""
    return {"status": "ok"}
