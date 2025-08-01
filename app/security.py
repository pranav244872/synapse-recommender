# app/security.py

import os
import secrets
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

# This defines the header we expect to receive.
# The Go backend will need to send a header called "X-Internal-API-Key"
api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)

# Load the expected API key from the environment variables.
# It's critical that your application is started with this variable set.
RECOMMENDER_API_KEY = os.getenv("RECOMMENDER_API_KEY")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Dependency function to validate the API key from the request header.
    """
    if not RECOMMENDER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key not configured on the server."
        )

    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key."
        )

    # Use a constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key_header, RECOMMENDER_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API Key."
        )

    return api_key_header # If successful, you could return the key or a simple True
