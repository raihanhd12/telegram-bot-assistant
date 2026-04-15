"""
User validators

Contains validation helpers for user creation and updates.
"""

from typing import Any, Dict

from src.app.schemas.user import UserCreate, UserUpdate


def validate_user_create(user_data: UserCreate) -> Dict[str, Any]:
    """Validate user creation data according to business rules.

    Returns a dict: {"valid": bool, "issues": List[str]}
    """
    issues = []

    # Username rule: letters, numbers, underscore, dash
    if not user_data.username.replace("_", "").replace("-", "").isalnum():
        issues.append(
            "Username can only contain letters, numbers, underscore, and dash"
        )

    # Basic email domain restrictions
    restricted_domains = ["tempmail.com", "throwaway.email"]
    email_domain = user_data.email.split("@")[1] if "@" in user_data.email else ""
    if email_domain in restricted_domains:
        issues.append("Email domain not allowed")

    # Password basic checks (presence/length). More rules can be added later.
    if not getattr(user_data, "password", None):
        issues.append("Password is required")
    elif len(user_data.password) < 6:
        issues.append("Password must be at least 6 characters long")

    return {"valid": len(issues) == 0, "issues": issues}


def validate_user_update(user_data: UserUpdate) -> Dict[str, Any]:
    """Validate user update data. Only validate provided fields."""
    issues = []

    data = user_data.model_dump(exclude_unset=True)

    username = data.get("username")
    email = data.get("email")

    if username is not None:
        if not username.replace("_", "").replace("-", "").isalnum():
            issues.append(
                "Username can only contain letters, numbers, underscore, and dash"
            )

    if email is not None:
        restricted_domains = ["tempmail.com", "throwaway.email"]
        email_domain = email.split("@")[1] if "@" in email else ""
        if email_domain in restricted_domains:
            issues.append("Email domain not allowed")

    # If password provided, check length
    password = data.get("password")
    if password is not None and len(password) < 6:
        issues.append("Password must be at least 6 characters long")

    return {"valid": len(issues) == 0, "issues": issues}
