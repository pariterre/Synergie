import logging
import requests
import socket

logger = logging.getLogger(__name__)


def has_internet_connection() -> bool:
    """
    Check if the computer is connected to the internet using both socket and HTTP methods.
    Returns:
        bool: True if internet connection is available, False otherwise.
    """
    # First, attempt a socket connection
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            sock.connect(("8.8.8.8", 53))
        logger.info("Internet connection verified via socket.")
        return True
    except:
        logging.debug("Checking internet via socket failed.")
        pass

    # If socket connection fails, attempt an HTTP request
    try:
        response = requests.get("https://www.google.com", timeout=3)
        if response.status_code == 200:
            logger.info("Internet connection verified via HTTP request.")
            return True
    except:
        logging.debug("Checking internet via HTTP request failed.")
        pass

    # If both methods fail, assume no internet connection
    logger.error("No internet connection detected.")
    return False
