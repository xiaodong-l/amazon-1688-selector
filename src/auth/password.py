"""
Password Hashing Module
Secure password handling using bcrypt for v2.3.0
"""

import bcrypt
from typing import Optional, Tuple


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Raises:
        ValueError: If password is empty or too short
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    
    # bcrypt has a 72 byte limit
    if len(password) > 72:
        password = password[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against
        
    Returns:
        True if password matches, False otherwise
        
    Raises:
        ValueError: If inputs are invalid
    """
    if not plain_password or not hashed_password:
        raise ValueError("Password and hash cannot be empty")
    
    try:
        # Truncate if needed
        if len(plain_password) > 72:
            plain_password = plain_password[:72]
        
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        # Handle any verification errors securely
        return False


def needs_rehash(hashed_password: str, target_rounds: int = 12) -> bool:
    """
    Check if a password hash needs to be rehashed.
    
    Args:
        hashed_password: Existing password hash
        target_rounds: Target bcrypt rounds
        
    Returns:
        True if rehashing is recommended
    """
    try:
        # Extract rounds from hash (format: $2b$12$...)
        parts = hashed_password.split('$')
        if len(parts) >= 3:
            current_rounds = int(parts[2])
            return current_rounds < target_rounds
        return True
    except Exception:
        return True


def rehash_password(password: str, old_hash: str) -> Optional[str]:
    """
    Rehash a password if the old hash needs updating.
    
    Args:
        password: Plain text password
        old_hash: Existing password hash
        
    Returns:
        New hash if rehashing was needed, None otherwise
    """
    if needs_rehash(old_hash):
        # Verify first, then rehash
        if verify_password(password, old_hash):
            return hash_password(password)
    return None


def validate_password_strength(password: str) -> Tuple[bool, list]:
    """
    Validate password strength according to security requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters")
    
    if len(password) > 128:
        issues.append("Password must be less than 128 characters")
    
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one number")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Password must contain at least one special character")
    
    return (len(issues) == 0, issues)
