"""
KOHA-CIL — Authentication Service
Handles user credential verification and password hashing utilities.
JWT generation is performed by the Security Gateway; the backend
only validates credentials and returns the user record.
"""
import logging
from typing import Optional

import bcrypt

from database.connection import get_db

logger = logging.getLogger(__name__)


def verify_credentials(username: str, password: str) -> Optional[dict]:
    """
    Verify username/password against the users table.

    Returns the user record dict on success, or None on failure.
    Never raises on invalid credentials — returns None instead.
    """
    try:
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT id, username, password_hash, role, subsidiary, is_active
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

        if row is None:
            logger.warning("Login attempt for unknown username: %s", username)
            return None

        user = dict(row)

        if not user.get("is_active", 1):
            logger.warning("Login attempt for inactive account: %s", username)
            return None

        # Constant-time bcrypt comparison
        pw_match = bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8"))
        if not pw_match:
            logger.warning("Invalid password for username: %s", username)
            return None

        # Strip sensitive field before returning
        del user["password_hash"]
        return user

    except Exception as exc:
        logger.error("Authentication error for %s: %s", username, exc)
        return None


def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt (12 rounds)."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
