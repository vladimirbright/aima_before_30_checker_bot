"""AIMA website scraper for checking application status."""

import re
from datetime import datetime
from typing import Dict
import httpx
from bs4 import BeautifulSoup
from app.config import settings


class LoginFailedException(Exception):
    """Raised when login fails."""
    pass


class StatusNotFoundException(Exception):
    """Raised when status table cannot be found in response."""
    pass


async def get_login_token(client: httpx.AsyncClient) -> str:
    """
    Fetch the login page and extract the CSRF token.

    Args:
        client: httpx AsyncClient with cookies enabled

    Returns:
        str: CSRF token value

    Raises:
        Exception: If token cannot be found
    """
    response = await client.get(settings.aima_login_url, timeout=30.0)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')

    # Find hidden input with name="tok"
    token_input = soup.find('input', {'name': 'tok', 'type': 'hidden'})

    if not token_input or not token_input.get('value'):
        raise Exception("CSRF token not found in login page")

    return token_input['value']


def sanitize_status_text(html_content: str) -> str:
    """
    Clean and sanitize status text from HTML.

    Args:
        html_content: Raw HTML content

    Returns:
        str: Cleaned text with normalized whitespace
    """
    # Parse HTML
    soup = BeautifulSoup(html_content, 'lxml')

    # Get text content
    text = soup.get_text()

    # Replace &nbsp; with space
    text = text.replace('\xa0', ' ')

    # Normalize whitespace but preserve line breaks
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    # Join with single newline
    return '\n'.join(cleaned_lines)


async def login_and_get_status(email: str, password: str) -> Dict:
    """
    Login to AIMA website and retrieve application status.

    Args:
        email: User email address
        password: User password

    Returns:
        dict: Response with status
            Success: {"status": "success", "status_text": "...", "timestamp": "..."}
            Error: {"status": "error", "error": "...", "timestamp": "..."}

    Raises:
        LoginFailedException: If login fails
        StatusNotFoundException: If status cannot be found
        httpx.TimeoutException: If request times out
    """
    timestamp = datetime.utcnow().isoformat()

    try:
        # Create client with cookies enabled
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0
        ) as client:

            # Step 1: Get CSRF token
            token = await get_login_token(client)

            # Step 2: Login
            login_data = {
                'email': email,
                'password': password,
                'tok': token
            }

            response = await client.post(
                settings.aima_check_url,
                data=login_data,
                timeout=30.0
            )

            # Check if login was successful
            # If login fails, AIMA usually redirects back to login page
            # or shows an error message
            if 'login.php' in str(response.url):
                raise LoginFailedException("Invalid email or password")

            # Step 3: Parse response HTML
            soup = BeautifulSoup(response.text, 'lxml')

            # Find table with background-color: salmon
            # The status is in: <table style="width: 100%"><tbody><tr><td style="background-color: salmon;">
            status_cell = None

            # Search for td with background-color: salmon
            for td in soup.find_all('td'):
                style = td.get('style', '')
                if 'background-color' in style and 'salmon' in style.lower():
                    status_cell = td
                    break

            if not status_cell:
                # Try alternative: look for table with salmon background
                for table in soup.find_all('table'):
                    for td in table.find_all('td'):
                        style = td.get('style', '')
                        if 'background-color' in style and 'salmon' in style.lower():
                            status_cell = td
                            break
                    if status_cell:
                        break

            if not status_cell:
                raise StatusNotFoundException(
                    "Could not find status table with salmon background"
                )

            # Extract and clean text
            status_html = str(status_cell)
            status_text = sanitize_status_text(status_html)

            return {
                "status": "success",
                "status_text": status_text,
                "timestamp": timestamp
            }

    except LoginFailedException as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": timestamp
        }

    except StatusNotFoundException as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": timestamp
        }

    except httpx.TimeoutException:
        return {
            "status": "error",
            "error": "Request timed out - AIMA website may be slow or unavailable",
            "timestamp": timestamp
        }

    except httpx.HTTPError as e:
        return {
            "status": "error",
            "error": f"HTTP error: {str(e)}",
            "timestamp": timestamp
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "timestamp": timestamp
        }
