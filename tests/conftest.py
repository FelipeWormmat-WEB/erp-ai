import os


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://erp_user:test@localhost:5432/erp_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-with-at-least-32-characters")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("SEED_USERNAME", "admin")
os.environ.setdefault("SEED_PASSWORD", "test-password")
