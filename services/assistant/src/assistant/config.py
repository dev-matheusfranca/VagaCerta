import os

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct")
MCP_URL = os.environ.get("MCP_URL", "http://localhost:8005/mcp")
TIMEZONE = os.environ.get("TIMEZONE", "America/Sao_Paulo")
