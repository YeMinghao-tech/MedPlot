"""Authentication middleware for API requests."""

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional


# Security scheme for OpenAPI docs
security_scheme = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware.

    Currently a pass-through middleware. In production:
    - Validate JWT tokens
    - Check API keys
    - Rate limiting
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and validate authentication.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response from downstream handler.
        """
        # Skip auth for health check and docs
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Skip auth for WebSocket upgrades
        if request.url.path.endswith("/ws"):
            return await call_next(request)

        # In production, validate token here:
        # auth_header = request.headers.get("Authorization")
        # if not auth_header or not self._validate_token(auth_header):
        #     raise HTTPException(status_code=401, detail="Unauthorized")

        response = await call_next(request)
        return response

    def _validate_token(self, auth_header: str) -> bool:
        """Validate authorization token.

        Args:
            auth_header: Authorization header value.

        Returns:
            True if valid, False otherwise.
        """
        # Placeholder - implement JWT/API key validation
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return len(token) > 0
        return False


def verify_api_key(api_key: Optional[str], expected_key: Optional[str] = None) -> bool:
    """Verify API key.

    Args:
        api_key: Provided API key.
        expected_key: Expected API key (from config in production).

    Returns:
        True if valid.
    """
    if not expected_key:
        # No auth configured - pass through
        return True
    if not api_key:
        return False
    return api_key == expected_key
