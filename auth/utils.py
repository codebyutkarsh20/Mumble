import re
from typing import Tuple, Optional

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """Simple email validation.

    Returns (is_valid, error_message)."""
    if not email:
        return False, "Email is required"
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format"
    return True, None


def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """Ensure password meets minimum requirements.

    Requirements:
    * At least 8 characters
    * Contains upper, lower, digit, and special char
    """
    if not password:
        return False, "Password is required"
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain an uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain a lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain a digit"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain a special character"
    return True, None