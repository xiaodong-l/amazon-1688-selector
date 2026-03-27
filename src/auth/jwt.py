"""
JWT Authentication Module
Handles token generation, verification, and refresh for v2.3.0
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError, ExpiredSignatureError
import os

# Configuration - In production, load from environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new access token with the given data.
    
    Args:
        data: Payload data to encode in the token (e.g., user_id, username)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a refresh token for token renewal.
    
    Args:
        data: Payload data to encode in the token
        
    Returns:
        Encoded refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If token is invalid
        ExpiredSignatureError: If token has expired
        ValueError: If token is blacklisted
    """
    # Check if token is blacklisted
    if is_token_blacklisted(token):
        raise ValueError("Token has been blacklisted")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise ExpiredSignatureError("Token has expired")
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")


def refresh_token(token: str) -> str:
    """
    Refresh an existing token to extend its validity.
    
    Args:
        token: Current JWT token to refresh
        
    Returns:
        New JWT token with extended expiration
        
    Raises:
        ValueError: If token cannot be refreshed
    """
    from .token_blacklist import blacklist_token as add_to_blacklist
    
    try:
        payload = verify_token(token)
        
        # Check token type
        if payload.get("type") not in ["access", "refresh"]:
            raise ValueError("Invalid token type for refresh")
        
        # Extract user data (exclude exp, iat, type)
        user_data = {k: v for k, v in payload.items() if k not in ["exp", "iat", "type"]}
        
        # Create new access token
        new_token = create_access_token(user_data)
        
        # Blacklist old token
        add_to_blacklist(token)
        
        return new_token
        
    except ExpiredSignatureError:
        # Allow refresh of expired tokens if they're not blacklisted
        if not is_token_blacklisted(token):
            try:
                # Decode without verification to get payload
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
                user_data = {k: v for k, v in payload.items() if k not in ["exp", "iat", "type"]}
                new_token = create_access_token(user_data)
                add_to_blacklist(token)
                return new_token
            except JWTError:
                raise ValueError("Cannot refresh invalid token")
        raise ValueError("Cannot refresh blacklisted token")


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is in the blacklist.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is blacklisted, False otherwise
    """
    from .token_blacklist import get_blacklist
    return get_blacklist().is_blacklisted(token)


def blacklist_token(token: str, expires_at: Optional[datetime] = None) -> bool:
    """
    Add a token to the blacklist.
    
    Args:
        token: JWT token to blacklist
        expires_at: When the blacklist entry expires (default: token's exp)
        
    Returns:
        True if successfully added
    """
    from .token_blacklist import get_blacklist
    
    try:
        if expires_at is None:
            # Decode to get expiration
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            exp = payload.get("exp")
            if exp:
                expires_at = datetime.fromtimestamp(exp)
            else:
                expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        return get_blacklist().add(token, expires_at)
    except Exception:
        return False


def cleanup_blacklist() -> int:
    """
    Remove expired entries from the blacklist.
    
    Returns:
        Number of entries removed
    """
    from .token_blacklist import get_blacklist
    return get_blacklist().cleanup_expired()
