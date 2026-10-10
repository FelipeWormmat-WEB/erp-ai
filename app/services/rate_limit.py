import time
from collections import defaultdict, deque
from typing import Deque

from app.core.config import get_settings


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, Deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> bool:
        settings = get_settings()
        now = time.monotonic()
        window_start = now - settings.login_rate_limit_window_seconds
        attempts = self._attempts[key]

        while attempts and attempts[0] < window_start:
            attempts.popleft()

        if len(attempts) >= settings.login_rate_limit_attempts:
            return False

        attempts.append(now)
        return True

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


login_rate_limiter = InMemoryRateLimiter()
