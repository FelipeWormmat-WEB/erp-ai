import os


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://erp_user:test@localhost:5432/erp_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("CACHE_TTL_SECONDS", "60")
os.environ.setdefault("REDIS_TIMEOUT_SECONDS", "0.2")
os.environ.setdefault("JWT_SECRET", "test-secret-with-at-least-32-characters")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("LOGIN_RATE_LIMIT_ATTEMPTS", "5")
os.environ.setdefault("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60")
os.environ.setdefault("SEED_USERNAME", "admin")
os.environ.setdefault("SEED_PASSWORD", "test-password")
