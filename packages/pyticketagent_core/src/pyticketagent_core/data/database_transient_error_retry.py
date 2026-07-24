"""Retry helper for transient database errors."""

from __future__ import annotations

import asyncio
import logging
import math
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pyticketagent_core.data.database_transient_error_classifier import (
    is_transient_exception,
)

T = TypeVar("T")

logger = logging.getLogger(__name__)


async def execute_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    initial_delay_ms: int = 200,
    max_delay_ms: int = 2000,
) -> T:
    """Run ``operation``, retrying on transient database errors.

    Uses exponential backoff with jitter, matching DFAgent's formula.
    ``max_attempts`` is the number of *retries* after the first failure
    (attempt 0 is the initial try; retries are 1..max_attempts).
    """
    attempt = 0
    while True:
        try:
            return await operation()
        except Exception as ex:
            if not is_transient_exception(ex):
                raise

            if attempt >= max_attempts:
                logger.error(
                    "Transient database error exhausted %s retries: %s",
                    max_attempts,
                    ex,
                )
                raise

            attempt += 1
            delay = _compute_delay(initial_delay_ms, max_delay_ms, attempt)
            logger.warning(
                "Transient database error, retry %s/%s in %.0fms: %s",
                attempt,
                max_attempts,
                delay * 1000,
                ex,
            )
            await asyncio.sleep(delay)


def _compute_delay(initial_delay_ms: int, max_delay_ms: int, attempt: int) -> float:
    exponential_ms = initial_delay_ms * math.pow(2, attempt - 1)
    capped_ms = min(exponential_ms, max_delay_ms)
    jitter_ms = random.randint(0, max(1, int(capped_ms * 0.1)))
    return (capped_ms + jitter_ms) / 1000.0
