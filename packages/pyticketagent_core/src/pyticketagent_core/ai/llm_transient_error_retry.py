"""Retry helper for transient LLM API errors."""

from __future__ import annotations

import asyncio
import logging
import math
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pyticketagent_core.ai.llm_api_error_classifier import (
    get_status_code,
    is_transient_exception,
)
from pyticketagent_core.ai.llm_transient_retry_options import LlmTransientRetryOptions

T = TypeVar("T")

logger = logging.getLogger(__name__)


async def execute_with_retry(
    operation: Callable[[], Awaitable[T]],
    options: LlmTransientRetryOptions,
) -> T:
    """Run ``operation``, retrying on transient LLM errors.

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

            if attempt >= options.max_attempts:
                logger.error(
                    "Transient LLM API error (HTTP %s) exhausted %s retries: %s",
                    get_status_code(ex),
                    options.max_attempts,
                    ex,
                )
                raise

            attempt += 1
            delay = _compute_delay(options, attempt)
            logger.warning(
                "Transient LLM API error (HTTP %s), retry %s/%s in %.0fms: %s",
                get_status_code(ex),
                attempt,
                options.max_attempts,
                delay * 1000,
                ex,
            )
            await asyncio.sleep(delay)


def _compute_delay(options: LlmTransientRetryOptions, attempt: int) -> float:
    exponential_ms = options.initial_delay_ms * math.pow(2, attempt - 1)
    capped_ms = min(exponential_ms, options.max_delay_ms)
    jitter_ms = random.randint(0, max(1, int(capped_ms * 0.1)))
    return (capped_ms + jitter_ms) / 1000.0
