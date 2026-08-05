"""
Security hardening module for input validation, SQL injection prevention, and security headers.
"""

import re
import logging
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Validation constraints
CLIP_TITLE_MAX_LENGTH = 255
CLIP_DESCRIPTION_MAX_LENGTH = 2000
CLIP_NOTES_MAX_LENGTH = 5000
USERNAME_MAX_LENGTH = 128
TAG_MAX_LENGTH = 50
TAGS_MAX_COUNT = 20
QUERY_MAX_LENGTH = 1000

# Dangerous SQL patterns to detect (basic checks)
SQL_INJECTION_PATTERNS = [
    r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|SCRIPT)\b)",
    r"(--|#|/\*|\*/)",  # SQL comments
    r"(;|\||&&)",  # Command separators
    r"('|\")\s*(OR|AND)\s*('|\")",  # OR 1=1 style attacks
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.",
    r"%2e%2e",
    r"\.\.\\",
]


class ValidationError(ValueError):
    """Raised when input validation fails"""
    pass


class SQLInjectionDetected(ValueError):
    """Raised when SQL injection attempt is detected"""
    pass


def sanitize_string(value: Optional[str], max_length: int = 1000, allow_special: bool = True) -> Optional[str]:
    """
    Sanitize a string input.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        allow_special: Whether to allow special characters

    Returns:
        Sanitized string or None
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValidationError("Input must be a string")

    # Remove null bytes
    value = value.replace('\x00', '')

    # Truncate if too long
    if len(value) > max_length:
        logger.warning(f"String truncated from {len(value)} to {max_length}")
        value = value[:max_length]

    # Strip leading/trailing whitespace
    value = value.strip()

    if not allow_special:
        # Keep only alphanumeric, spaces, hyphens, underscores
        value = re.sub(r'[^a-zA-Z0-9\s\-_]', '', value)

    return value


def validate_clip_title(title: Optional[str]) -> Optional[str]:
    """Validate clip title"""
    if title is None:
        return None

    title = sanitize_string(title, max_length=CLIP_TITLE_MAX_LENGTH, allow_special=True)

    if not title:
        raise ValidationError("Title cannot be empty")

    # Allow alphanumeric, spaces, basic punctuation
    if not re.match(r'^[a-zA-Z0-9\s\-_.!?,\'"()&:\[\]]*$', title):
        raise ValidationError("Title contains invalid characters")

    return title


def validate_clip_description(description: Optional[str]) -> Optional[str]:
    """Validate clip description"""
    if description is None:
        return None

    return sanitize_string(description, max_length=CLIP_DESCRIPTION_MAX_LENGTH, allow_special=True)


def validate_clip_notes(notes: Optional[str]) -> Optional[str]:
    """Validate clip notes"""
    if notes is None:
        return None

    return sanitize_string(notes, max_length=CLIP_NOTES_MAX_LENGTH, allow_special=True)


def validate_tags(tags: Optional[list]) -> Optional[list]:
    """Validate clip tags"""
    if tags is None:
        return None

    if not isinstance(tags, list):
        raise ValidationError("Tags must be a list")

    if len(tags) > TAGS_MAX_COUNT:
        raise ValidationError(f"Too many tags (max {TAGS_MAX_COUNT})")

    validated = []
    for tag in tags:
        if not isinstance(tag, str):
            raise ValidationError("Each tag must be a string")

        tag = sanitize_string(tag, max_length=TAG_MAX_LENGTH, allow_special=False)
        if tag:
            validated.append(tag)

    return validated if validated else None


def validate_file_path(file_path: str, base_dir: str) -> bool:
    """
    Validate file path to prevent traversal attacks.

    Args:
        file_path: File path to validate
        base_dir: Base directory that file must be under

    Returns:
        True if valid, raises ValidationError otherwise
    """
    if not file_path or not isinstance(file_path, str):
        raise ValidationError("Invalid file path")

    # Check for path traversal patterns
    upper_path = file_path.upper()
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, upper_path, re.IGNORECASE):
            raise ValidationError("Path traversal detected")

    # Normalize and resolve the path
    import os
    from pathlib import Path

    try:
        resolved = Path(base_dir).resolve() / file_path
        resolved_path = resolved.resolve()
        base_resolved = Path(base_dir).resolve()

        # Ensure resolved path is under base directory
        if not str(resolved_path).startswith(str(base_resolved)):
            raise ValidationError("File path is outside allowed directory")

        return True
    except Exception as e:
        raise ValidationError(f"Invalid file path: {str(e)}")


def check_sql_injection(value: Optional[str]) -> bool:
    """
    Check if a string contains likely SQL injection patterns.
    NOTE: This is a basic heuristic check. Use parameterized queries for real protection.

    Args:
        value: String to check

    Returns:
        True if injection likely, False otherwise
    """
    if not value or not isinstance(value, str):
        return False

    upper_val = value.upper()

    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, upper_val):
            logger.warning(f"SQL injection pattern detected: {pattern}")
            return True

    return False


def validate_user_input(
    value: str,
    max_length: int = 1000,
    allow_sql_keywords: bool = False,
    allow_special: bool = True
) -> str:
    """
    Comprehensive user input validation.

    Args:
        value: Input to validate
        max_length: Maximum allowed length
        allow_sql_keywords: Whether to allow SQL keywords
        allow_special: Whether to allow special characters

    Returns:
        Validated string

    Raises:
        ValidationError: If validation fails
        SQLInjectionDetected: If SQL injection pattern detected
    """
    if not isinstance(value, str):
        raise ValidationError("Input must be a string")

    # Null byte check
    if '\x00' in value:
        raise ValidationError("Null bytes not allowed")

    # Length check
    if len(value) > max_length:
        raise ValidationError(f"Input exceeds maximum length of {max_length}")

    # SQL injection check (when needed)
    if not allow_sql_keywords and check_sql_injection(value):
        raise SQLInjectionDetected("Input contains suspicious SQL patterns")

    return sanitize_string(value, max_length, allow_special)


def validate_email(email: str) -> str:
    """Validate email address"""
    if not isinstance(email, str):
        raise ValidationError("Email must be a string")

    email = email.strip().lower()

    if len(email) > 254:  # RFC 5321
        raise ValidationError("Email too long")

    # Basic email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError("Invalid email format")

    return email


def validate_username(username: str) -> str:
    """Validate username"""
    if not isinstance(username, str):
        raise ValidationError("Username must be a string")

    username = sanitize_string(username, max_length=USERNAME_MAX_LENGTH)

    if not username:
        raise ValidationError("Username cannot be empty")

    # Alphanumeric, hyphens, underscores only
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise ValidationError("Username can only contain letters, numbers, hyphens, and underscores")

    # No leading/trailing hyphens or underscores
    if username.startswith(('_', '-')) or username.endswith(('_', '-')):
        raise ValidationError("Username cannot start or end with hyphens or underscores")

    return username


def validate_url(url: str, allowed_schemes: list = None) -> str:
    """Validate URL"""
    if not isinstance(url, str):
        raise ValidationError("URL must be a string")

    if len(url) > 2048:
        raise ValidationError("URL too long")

    if not allowed_schemes:
        allowed_schemes = ['http', 'https']

    pattern = r'^(' + '|'.join(allowed_schemes) + r')://[^\s/$.?#].[^\s]*$'
    if not re.match(pattern, url, re.IGNORECASE):
        raise ValidationError("Invalid URL format")

    return url


def get_safe_attribute(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute to prevent info disclosure"""
    try:
        return getattr(obj, attr, default)
    except:
        return default


class SecurityHeaders:
    """Security headers middleware data"""

    @staticmethod
    def get_headers(is_prod: bool = True) -> dict:
        """Get recommended security headers"""
        headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent MIME sniffing
            "X-Content-Type-Options": "nosniff",
            # XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
        }

        if is_prod:
            # Strict HSTS in production
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            # Stricter CSP in production
            headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        else:
            # More permissive CSP in dev
            headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-eval'; "
                "script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss:"
            )

        return headers
