from app.core.config import get_settings
from app.services.rate_limit import InMemoryRateLimiter


def test_login_rate_limiter_blocks_after_configured_attempts() -> None:
    settings = get_settings()
    limiter = InMemoryRateLimiter()
    key = "127.0.0.1:admin"

    for _ in range(settings.login_rate_limit_attempts):
        assert limiter.hit(key)

    assert not limiter.hit(key)

    limiter.reset(key)
    assert limiter.hit(key)
