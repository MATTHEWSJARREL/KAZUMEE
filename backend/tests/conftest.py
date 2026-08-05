"""
Pytest configuration and shared fixtures for all tests.
Provides database, auth, and utility fixtures for the test suite.
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.database.session import Base
from backend.database.models.user import User
from backend.database.models.streamer import Streamer
from backend.database.models.stream_session import StreamSession
from backend.database.models.clip import Clip
from backend.database.models.user_session import UserSession
from backend.core.auth import create_session_token, hash_token


# Use in-memory SQLite for fast tests
@pytest.fixture(scope="session")
def test_db_engine():
    """Create an in-memory database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(test_db_engine):
    """Create a new database session for each test"""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user"""
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        role="streamer",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_streamer(db_session: Session, test_user: User):
    """Create a test streamer"""
    streamer = Streamer(
        id=1,
        user_id=test_user.id,
        username="teststreamer",
        display_name="Test Streamer",
        platform="twitch",
        platform_user_id="twitch_123",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(streamer)
    db_session.commit()
    db_session.refresh(streamer)
    return streamer


@pytest.fixture
def test_stream_session(db_session: Session, test_streamer: Streamer):
    """Create a test stream session"""
    session = StreamSession(
        id=1,
        streamer_id=test_streamer.id,
        status="live",
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def test_clip(db_session: Session, test_streamer: Streamer, test_stream_session: StreamSession):
    """Create a test clip"""
    clip = Clip(
        id=1,
        stream_session_id=test_stream_session.id,
        streamer_id=test_streamer.id,
        title="Test Clip",
        description="A test clip",
        file_path="backend/data/clips/extracted/test_clip.mp4",
        status="pending",
        requested_by_type="auto_detection",
        requested_by_name="Test AI",
        duration_seconds=45,
        quality_score=0.85,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(clip)
    db_session.commit()
    db_session.refresh(clip)
    return clip


@pytest.fixture
def auth_token(test_user: User):
    """Create a valid auth token for test user"""
    token = create_session_token(test_user.id, expiry_hours=24)
    return token


@pytest.fixture
def expired_token(test_user: User):
    """Create an expired auth token"""
    from backend.database.models.user_session import UserSession

    token = "expired_token_12345"
    hashed = hash_token(token)

    # Create expired session
    session = UserSession(
        user_id=test_user.id,
        token_hash=hashed,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
        ip_address="127.0.0.1",
        user_agent="test-client",
    )
    return token


# Test configuration
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (slower, full workflow)"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as related to authentication"
    )
    config.addinivalue_line(
        "markers", "security: mark test as related to security"
    )
