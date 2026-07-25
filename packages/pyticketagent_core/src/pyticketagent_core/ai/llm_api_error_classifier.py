"""Classify LLM API errors as transient or permanent."""

from __future__ import annotations

import httpx

_QUOTA_OR_BILLING_KEYWORDS = (
    "quota",
    "resource_exhausted",
    "resource exhausted",
    "billing",
    "payment required",
    "exceeded your",
    "limit exceeded",
    "insufficient credits",
)

_RATE_LIMIT_KEYWORDS = (
    "rate limit",
    "rate_limit",
    "ratelimit",
    "too many requests",
    "concurrent",
    "throttl",
)


def get_status_code(ex: BaseException) -> int:
    """Best-effort HTTP status extraction from SDK / httpx exceptions."""
    status = getattr(ex, "status_code", None)
    if isinstance(status, int):
        return status

    response = getattr(ex, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code

    if isinstance(ex, httpx.HTTPStatusError):
        return ex.response.status_code

    return 0


def is_quota_or_billing_error(ex: BaseException) -> bool:
    text = _exception_text(ex)
    return any(keyword in text for keyword in _QUOTA_OR_BILLING_KEYWORDS)


def is_retryable_429(ex: BaseException) -> bool:
    if get_status_code(ex) != 429:
        return False
    if is_quota_or_billing_error(ex):
        return False
    if _has_retry_after(ex):
        return True
    text = _exception_text(ex)
    return any(keyword in text for keyword in _RATE_LIMIT_KEYWORDS)


def is_transient_exception(ex: BaseException) -> bool:
    status_code = get_status_code(ex)
    if status_code in (408, 500, 502, 503, 504):
        return True
    if status_code == 429:
        return is_retryable_429(ex)
    if isinstance(ex, (httpx.TimeoutException, httpx.TransportError)):
        return True
    return False


def _has_retry_after(ex: BaseException) -> bool:
    text = _exception_text(ex)
    return "retry-after" in text or "retry after" in text


def _exception_text(ex: BaseException) -> str:
    parts: list[str] = []
    current: BaseException | None = ex
    while current is not None:
        if current.args:
            parts.append(str(current))
        current = current.__cause__ or current.__context__
        if current is ex:
            break
    return " ".join(parts).casefold()
