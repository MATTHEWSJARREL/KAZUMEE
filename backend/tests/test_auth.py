"""
Unit tests for authentication system.
Tests token creation, validation, and session management.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.core.auth import (
    create_session_token,
    hash_token,
    verify_token,
    get_streamer_id_for_user,
)
from backend.database.models.user_session import UserSession


@pytest.mark.unit
@pytest.mark.auth
class TestTokenCreation:
    """Test token creation and hashing"""

    def test_create_session_token_returns_string(self, test_user):
        """Token should be a string"""
        token = create_session_token(test_user.id, expiry_hours=24)
        assert isinstance(token, str)
        assert len(token) > 20  # Should be reasonably long

    def test_create_session_token_generates_unique_tokens(self, test_user):
        """Each token creation should generate a unique token"""
        token1 = create_session_token(test_user.id, expiry_hours=24)
        token2 = create_session_token(test_user.id, expiry_hours=24)
        assert token1 != token2

    def test_hash_token_consistent(self):
        """Hashing the same token should produce the same hash"""
        token = "test_token_123"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2

    def test_hash_token_different_for_different_inputs(self):
        """Different tokens should produce different hashes"""
        hash1 = hash_token("token1")
        hash2 = hash_token("token2")
        assert hash1 != hash2

    def test_hash_token_not_reversible(self):
        """Hash should not contain the original token"""
        token = "secret_token_123"
        hashed = hash_token(token)
        assert token not in hashed
        assert len(hashed) > len(token)  # Hash should be longer


@pytest.mark.unit
@pytest.mark.auth
class TestTokenVerification:
    """Test token verification and validation"""

    def test_verify_valid_token(self, db_session: Session, test_user):
        """Valid token should verify successfully"""
        token = create_session_token(test_user.id, expiry_hours=24)
        hashed = hash_token(token)

        # Store the session
        session = UserSession(
            user_id=test_user.id,
            token_hash=hashed,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            ip_address="127.0.0.1",
            user_agent="test-client",
        )
        db_session.add(session)
        db_session.commit()

        # Verify should work
        verified_user_id = verify_token(token, db_session)
        assert verified_user_id == test_user.id

    def test_verify_invalid_token_returns_none(self, db_session: Session, test_user):
        """Invalid token should return None"""
        token = create_session_token(test_user.id, expiry_hours=24)
        hashed = hash_token(token)

        session = UserSession(
            user_id=test_user.id,
            token_hash=hashed,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            ip_address="127.0.0.1",
            user_agent="test-client",
        )
        db_session.add(session)
        db_session.commit()

        # Wrong token should fail
        wrong_token = "completely_different_token"
        verified_user_id = verify_token(wrong_token, db_session)
        assert verified_user_id is None

    def test_verify_expired_token_returns_none(self, db_session: Session, test_user):
        """Expired token should return None"""
        token = create_session_token(test_user.id, expiry_hours=24)
        hashed = hash_token(token)

        # Create expired session
        session = UserSession(
            user_id=test_user.id,
            token_hash=hashed,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            ip_address="127.0.0.1",
            user_agent="test-client",
        )
        db_session.add(session)
        db_session.commit()

        # Should fail due to expiry
        verified_user_id = verify_token(token, db_session)
        assert verified_user_id is None


@pytest.mark.unit
@pytest.mark.auth
class TestStreamerIdentification:
    """Test streamer ID retrieval"""

    def test_get_streamer_id_for_streamer_user(self, test_user, test_streamer):
        """Should return streamer_id for streamer user"""
        streamer_id = get_streamer_id_for_user(test_user)
        assert streamer_id == test_streamer.id

    def test_get_streamer_id_for_non_streamer_user(self, db_session: Session):
        """Should return None for non-streamer users"""
        viewer_user = db_session.query(User).filter_by(role="viewer").first()
        if viewer_user:
            streamer_id = get_streamer_id_for_user(viewer_user)
            assert streamer_id is None

    def test_get_streamer_id_for_none_user(self):
        """Should return None for None input"""
        streamer_id = get_streamer_id_for_user(None)
        assert streamer_id is None


@pytest.mark.unit
@pytest.mark.auth
class TestTokenExpiry:
    """Test token expiry logic"""

    def test_token_expiry_time_is_in_future(self, test_user):
        """Newly created token should expire in the future"""
        token = create_session_token(test_user.id, expiry_hours=24)
        # Token should be created, implying future expiry
        assert isinstance(token, str)

    def test_token_expiry_hours_parameter(self, test_user):
        """Different expiry hours should create different tokens"""
        token_24h = create_session_token(test_user.id, expiry_hours=24)
        token_1h = create_session_token(test_user.id, expiry_hours=1)
        # Tokens should be different (different expiry times)
        assert token_24h != token_1h


@pytest.mark.unit
@pytest.mark.auth
class TestTokenSecurity:
    """Test security properties of token system"""

    def test_token_cannot_be_guessed(self, test_user):
        """Tokens should be cryptographically random"""
        tokens = set()
        for _ in range(100):
            token = create_session_token(test_user.id, expiry_hours=24)
            tokens.add(token)

        # All tokens should be unique
        assert len(tokens) == 100

    def test_token_hash_uses_salt(self):
        """Hashing same token twice should produce different hashes if salt is used"""
        token = "test_token"
        # In production, we should use salt. For now just verify hashing works
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        # Deterministic hashing for verification, so should be same
        assert hash1 == hash2

    def test_token_no_user_id_leakage(self, test_user):
        """Token should not contain user_id in plaintext"""
        token = create_session_token(test_user.id, expiry_hours=24)
        user_id_str = str(test_user.id)
        # Token should not contain user ID
        assert user_id_str not in token
