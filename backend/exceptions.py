"""
Custom exceptions for policy website extraction.
Error codes are designed for frontend to branch on (e.g. prompt for credentials).
"""

# Error codes for frontend branching
POLICY_FETCH_AUTH_REQUIRED = "POLICY_FETCH_AUTH_REQUIRED"
POLICY_FETCH_FORBIDDEN = "POLICY_FETCH_FORBIDDEN"
POLICY_FETCH_NETWORK_ERROR = "POLICY_FETCH_NETWORK_ERROR"
POLICY_FETCH_PARSE_ERROR = "POLICY_FETCH_PARSE_ERROR"
POLICY_FETCH_NOT_FOUND = "POLICY_FETCH_NOT_FOUND"
POLICY_FETCH_ERROR = "POLICY_FETCH_ERROR"


class PolicyFetchError(Exception):
    """Base exception for policy fetch failures."""

    def __init__(self, message: str, code: str = POLICY_FETCH_ERROR, http_status: int | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


class PolicyFetchAuthRequiredError(PolicyFetchError):
    """Page requires authentication; frontend should prompt for credentials."""

    def __init__(self, message: str = "Authentication required to access this policy page"):
        super().__init__(message, code=POLICY_FETCH_AUTH_REQUIRED, http_status=401)


class PolicyFetchForbiddenError(PolicyFetchError):
    """Access forbidden."""

    def __init__(self, message: str = "Access forbidden to this policy page"):
        super().__init__(message, code=POLICY_FETCH_FORBIDDEN, http_status=403)


class PolicyFetchNetworkError(PolicyFetchError):
    """Network, timeout, or DNS failure."""

    def __init__(self, message: str):
        super().__init__(message, code=POLICY_FETCH_NETWORK_ERROR, http_status=502)


class PolicyFetchParseError(PolicyFetchError):
    """Response not valid HTML or conversion to markdown failed."""

    def __init__(self, message: str):
        super().__init__(message, code=POLICY_FETCH_PARSE_ERROR, http_status=422)


class PolicyFetchNotFoundError(PolicyFetchError):
    """Page not found."""

    def __init__(self, message: str = "Policy page not found"):
        super().__init__(message, code=POLICY_FETCH_NOT_FOUND, http_status=404)
