import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://vagacerta:vagacerta@localhost:5435/notification"
)
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
WEB_URL = os.environ.get("WEB_URL", "http://localhost:8080")
