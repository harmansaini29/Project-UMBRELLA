"""
Configuration
Contains connection pool limits and service parameters.
"""

import os

# Connection pool settings - Intentionally constrained for predictable incident demonstration
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./payment_db.sqlite")
POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "2"))
MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "0"))
POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "1.0"))
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8001"))
