import sys
from unittest.mock import MagicMock

# Mock heavy ML and DB dependencies to allow local testing without installing them
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["langchain_openai"] = MagicMock()
sys.modules["sqlalchemy"] = MagicMock()



import os

# Adjust path so test runner can find modules inside api/ and airflow/plugins/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(project_root, "api"))
sys.path.insert(0, os.path.join(project_root, "airflow", "plugins"))
sys.path.insert(0, os.path.join(project_root, "airflow"))

# Set mock env variables for testing
os.environ["RAG_DATABASE_URL"] = "postgresql+psycopg2://postgres:postgres@localhost:5432/test_db"
os.environ["EMBEDDING_MODEL_NAME"] = "sentence-transformers/all-MiniLM-L6-v2"
os.environ["DATA_DIR"] = "/tmp/data"
os.environ["OPENAI_API_KEY"] = ""

