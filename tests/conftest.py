"""tests/conftest.py: Pytest configuration with isolated test database."""

import os
import pytest

# Ensure tests use an isolated in-memory SQLite database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Set empty keys during tests for fast, deterministic offline execution
for key in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY"]:
    os.environ[key] = ""

from core.db.session import Base, engine, SessionLocal


@pytest.fixture(autouse=True)
def clean_db():
    """Recreate tables before each test for total isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
