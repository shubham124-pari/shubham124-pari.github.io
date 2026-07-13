"""
Shared pytest fixtures.

Deliberately does NOT connect to a real MySQL database. Every test
mocks the model-layer functions (models.user.*, etc.) instead, so the
whole suite runs anywhere with just `pip install -r requirements.txt` —
no database setup, no .env required. This tests routing, validation,
and auth logic; it does not test the actual SQL queries (that would
need an integration suite against a real/test database — worth adding
later, but out of scope for this first pass).
"""

import os
import sys

# Make `server/` importable the same way `python app.py` would run it
# (app.py itself uses bare imports like `from config import Config`,
# which only work if server/ is on sys.path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# FLASK_ENV must not be "production" here, or Config.validate() will
# raise unless a real JWT_SECRET_KEY is set in the environment.
os.environ.setdefault("FLASK_ENV", "testing")

from app import app as flask_app  # noqa: E402


@pytest.fixture
def app():
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
