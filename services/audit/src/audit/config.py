import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://vagacerta@localhost:5438/audit")
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER", "http://localhost:8080/auth/realms/vagacerta")
KEYCLOAK_JWKS_URL = os.environ.get(
    "KEYCLOAK_JWKS_URL", f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
)
TOPICS = ("booking.events", "waitlist.events")
