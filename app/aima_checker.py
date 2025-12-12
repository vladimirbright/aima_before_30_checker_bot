"""AIMA website scraper for checking application status."""

import re
import logging
from datetime import datetime
from typing import Dict
import httpx
from bs4 import BeautifulSoup
from app.config import settings


logger = logging.getLogger(__name__)


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
    response = await client.get(settings.aima_login_url)
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
        html_content: Raw HTML content (typically from <ul> tag)

    Returns:
        str: Cleaned text with normalized whitespace
    """
    import re

    # Parse HTML
    soup = BeautifulSoup(html_content, 'lxml')

    # Replace <br> tags with space before extracting text
    for br in soup.find_all('br'):
        br.replace_with(' ')

    # Remove any <b> tags (keep text, just remove formatting)
    for b_tag in soup.find_all('b'):
        b_tag.unwrap()

    # Get text content
    text = soup.get_text()

    # Replace &nbsp; with regular space
    text = text.replace('\xa0', ' ')

    # Clean up multiple spaces and whitespace
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


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

    logger.info(f"Starting AIMA status check for {email}")
    logger.debug(f"SSL verification: {settings.verify_ssl}")
    logger.debug(f"Login URL: {settings.aima_login_url}")
    logger.debug(f"Check URL: {settings.aima_check_url}")

    try:
        # Create client with cookies enabled
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            verify=settings.verify_ssl
        ) as client:

            logger.debug("Created HTTP client")

            # Step 1: Get CSRF token
            logger.debug("Fetching CSRF token...")
            token = await get_login_token(client)
            logger.debug(f"Got CSRF token: {token[:20]}...")

            # Step 2: Login
            login_data = {
                'email': email,
                'password': password,
                'tok': token
            }

            logger.debug("Posting login request...")
            response = await client.post(
                settings.aima_check_url,
                data=login_data
            )
            logger.debug(f"Login response status: {response.status_code}")
            logger.debug(f"Login response URL: {response.url}")

            # Check if login was successful
            # If login fails, AIMA usually redirects back to login page
            # or shows an error message
            if 'login.php' in str(response.url):
                logger.warning("Login failed - redirected to login page")
                raise LoginFailedException("Invalid email or password")

            # Step 3: Check for JavaScript redirect
            logger.debug("Checking for JavaScript redirect...")
            soup_initial = BeautifulSoup(response.text, 'lxml')

            # Look for JavaScript redirect: window.location.href="..."
            scripts = soup_initial.find_all('script')
            redirect_url = None

            for script in scripts:
                if script.string and 'window.location.href' in script.string:
                    # Extract URL from: window.location.href="/RAR/2fase/sumario.php"
                    import re
                    match = re.search(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', script.string)
                    if match:
                        redirect_url = match.group(1)
                        logger.debug(f"Found JavaScript redirect to: {redirect_url}")
                        break

            # If there's a JavaScript redirect, follow it
            if redirect_url:
                # Make sure it's an absolute URL
                if redirect_url.startswith('/'):
                    # Extract base URL from response.url
                    from urllib.parse import urljoin
                    redirect_url = urljoin(str(response.url), redirect_url)

                logger.debug(f"Following JavaScript redirect to: {redirect_url}")
                response = await client.get(redirect_url)
                logger.debug(f"Redirect response status: {response.status_code}")

            # Save response to file for debugging
            try:
                with open('/tmp/aima_response.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.debug("Saved final response HTML to /tmp/aima_response.html")
            except Exception as e:
                logger.warning(f"Could not save response HTML: {e}")

            # Step 4: Parse response HTML
            logger.debug("Parsing response HTML...")
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
                logger.error("Status table not found in response")
                raise StatusNotFoundException(
                    "Could not find status table with salmon background"
                )

            # Extract and clean text
            logger.debug("Extracting and sanitizing status text...")
            status_html = str(status_cell)
            logger.debug(f"Raw status HTML (first 500 chars): {status_html[:500]}")

            # The actual status text is in a <ul> tag inside the td
            ul_tag = status_cell.find('ul')
            if ul_tag:
                logger.debug("Found <ul> tag with status text")
                status_text = sanitize_status_text(str(ul_tag))
            else:
                logger.debug("No <ul> tag found, using entire cell content")
                status_text = sanitize_status_text(status_html)

            logger.debug(f"Sanitized status text: {status_text}")

            logger.info("Status check successful")
            return {
                "status": "success",
                "status_text": status_text,
                "timestamp": timestamp
            }

    except LoginFailedException as e:
        logger.error(f"Login failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": timestamp
        }

    except StatusNotFoundException as e:
        logger.error(f"Status not found: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": timestamp
        }

    except httpx.TimeoutException as e:
        logger.error(f"Request timeout: {e}")
        return {
            "status": "error",
            "error": "Request timed out - AIMA website may be slow or unavailable",
            "timestamp": timestamp
        }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"HTTP error: {str(e)}",
            "timestamp": timestamp
        }

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "timestamp": timestamp
        }
