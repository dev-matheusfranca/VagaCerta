import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://vagacerta@localhost:5436/waitlist"
)
CATALOG_URL = os.environ.get("CATALOG_URL", "http://localhost:8001")
BOOKING_URL = os.environ.get("BOOKING_URL", "http://localhost:8002")
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
OFFER_MINUTES = int(os.environ.get("OFFER_MINUTES", "15"))
KEYCLOAK_TOKEN_URL = os.environ.get(
    "KEYCLOAK_TOKEN_URL",
    "http://localhost:8080/auth/realms/vagacerta/protocol/openid-connect/token",
)
CLIENT_ID = os.environ.get("CLIENT_ID", "waitlist-service")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "waitlist-dev-secret")
