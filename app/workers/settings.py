from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.reports import generate_low_stock_report


class WorkerSettings:
    functions = [generate_low_stock_report]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
    max_tries = 3
    job_timeout = 30
    keep_result = 3600
    health_check_interval = 10
