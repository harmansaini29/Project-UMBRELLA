import os
DATABASE_URL = os.environ.get("DEMO_DATABASE_URL", "sqlite:///./demo_booking_db.sqlite")
POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "20"))
MAX_OVERFLOW = int(os.environ.get("DEMO_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = float(os.environ.get("DEMO_POOL_TIMEOUT", "1.0"))
SERVICE_PORT = int(os.environ.get("DEMO_SERVICE_PORT", "8002"))
