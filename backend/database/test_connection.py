import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
RUN_DB_TESTS = os.getenv("RUN_DB_TESTS", "").lower() in {"1", "true", "yes"}


@pytest.mark.skipif(
    not RUN_DB_TESTS,
    reason="Set RUN_DB_TESTS=1 to run database connectivity checks.",
)
def test_database_connection():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL not configured.")

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar_one()

    assert result == 1
