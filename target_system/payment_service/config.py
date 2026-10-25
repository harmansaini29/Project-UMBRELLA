"""
Payment Service Configuration
Contains connection pool limits and service parameters.
"""

import os

# Connection pool settings - initially restricted to demonstrate bottleneck
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./payment_db.sqlite")
POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "5"))
POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "1.0"))
SERVICE_PORT = int(os.environ.get("PAYMENT_SERVICE_PORT", "8001"))
