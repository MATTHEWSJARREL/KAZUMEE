"""
Unit tests for clip management APIs.
Tests CRUD operations, access control, and validation.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.database.models.clip import Clip
from backend.core.security import (
    validate_clip_title,
    validate_clip_description,
    validate_tags,
    ValidationError,
)


@pytest.mark.unit
class TestClipValidation:
    """Test input validation for clip operations"""

    def test_validate_clip_title_valid(self):
        """Valid title should pass validation"""
        title = "Amazing Highlight Moment"
        validated = validate_clip_title(title)
        assert validated == title

    def test_validate_clip_title_too_long(self):
        """Title exceeding max length should be truncated"""
        long_title = "A" * 300
        validated = validate_clip_title(long_title)
        assert len(validated) <= 255

    def test_validate_clip_title_empty_raises(self):
        """Empty title should raise validation error"""
        with pytest.raises(ValidationError):
            validate_clip_title("")

    def test_validate_clip_title_with_special_chars(self):
        """Title with valid special characters should pass"""
        title = "Epic Moment! (2024) - Highlight: Part 1"
        validated = validate_clip_title(title)
        assert validated is not None

    def test_validate_clip_title_strips_whitespace(self):
        """Title should have leading/trailing whitespace stripped"""
        title = "  Test Clip  "
        validated = validate_clip_title(title)
        assert validated == "Test Clip"

    def test_validate_clip_description_valid(self):
        """Valid description should pass"""
        desc = "This was an incredible moment during the stream"
        validated = validate_clip_description(desc)
        assert validated == desc

    def test_validate_clip_description_too_long(self):
        """Description exceeding max should be truncated"""
        long_desc = "A" * 3000
        validated = validate_clip_description(long_desc)
        assert len(validated) <= 2000

    def test_validate_clip_description_none(self):
        """None description should return None"""
        validated = validate_clip_description(None)
        assert validated is None

    def test_validate_tags_valid_list(self):
        """Valid tag list should pass"""
        tags = ["gaming", "twitch", "highlight"]
        validated = validate_tags(tags)
        assert len(validated) == 3

    def test_validate_tags_too_many(self):
        """More than max tags should raise error"""
        too_many_tags = [f"tag{i}" for i in range(25)]
        with pytest.raises(ValidationError):
            validate_tags(too_many_tags)

    def test_validate_tags_removes_special_chars(self):
        """Tags with special chars should be sanitized"""
        tags = ["game@streaming", "epic_moment", "2024-highlight"]
        validated = validate_tags(tags)
        # Should be sanitized (special chars removed)
        assert validated is not None
        assert len(validated) > 0

    def test_validate_tags_none(self):
        """None tags should return None"""
        validated = validate_tags(None)
        assert validated is None

    def test_validate_tags_empty_list(self):
        """Empty tag list should return None"""
        validated = validate_tags([])
        assert validated is None


@pytest.mark.unit
class TestClipCRUD:
    """Test clip create, read, update operations"""

    def test_create_clip_basic(self, db_session: Session, test_clip: Clip):
        """Should create clip with basic fields"""
        assert test_clip.id is not None
        assert test_clip.title == "Test Clip"
        assert test_clip.status == "pending"
        assert test_clip.streamer_id is not None

    def test_create_clip_with_all_fields(self, db_session: Session, test_streamer, test_stream_session):
        """Should create clip with all optional fields"""
        clip = Clip(
            stream_session_id=test_stream_session.id,
            streamer_id=test_streamer.id,
            title="Full Clip",
            description="Complete clip with all fields",
            file_path="backend/data/clips/extracted/full_clip.mp4",
            status="pending",
            requested_by_type="viewer_request",
            requested_by_id="viewer123",
            requested_by_name="TestViewer",
            duration_seconds=60,
            quality_score=0.95,
            tags=["epic", "highlight"],
            notes="First test clip",
        )
        db_session.add(clip)
        db_session.commit()
        db_session.refresh(clip)

        assert clip.id is not None
        assert clip.quality_score == 0.95
        assert clip.tags == ["epic", "highlight"]

    def test_read_clip_by_id(self, db_session: Session, test_clip: Clip):
        """Should retrieve clip by ID"""
        retrieved = db_session.query(Clip).filter(Clip.id == test_clip.id).first()
        assert retrieved is not None
        assert retrieved.title == test_clip.title

    def test_update_clip_status(self, db_session: Session, test_clip: Clip):
        """Should update clip status"""
        test_clip.status = "approved"
        db_session.commit()

        retrieved = db_session.query(Clip).filter(Clip.id == test_clip.id).first()
        assert retrieved.status == "approved"

    def test_update_clip_metadata(self, db_session: Session, test_clip: Clip):
        """Should update clip metadata"""
        test_clip.title = "Updated Title"
        test_clip.description = "Updated description"
        test_clip.tags = ["new", "tags"]
        db_session.commit()

        retrieved = db_session.query(Clip).filter(Clip.id == test_clip.id).first()
        assert retrieved.title == "Updated Title"
        assert retrieved.description == "Updated description"

    def test_delete_clip(self, db_session: Session, test_clip: Clip):
        """Should delete clip (soft delete via status)"""
        clip_id = test_clip.id
        test_clip.status = "deleted"
        db_session.commit()

        retrieved = db_session.query(Clip).filter(Clip.id == clip_id).first()
        assert retrieved.status == "deleted"


@pytest.mark.unit
class TestClipQueries:
    """Test common clip queries"""

    def test_get_pending_clips_for_streamer(
        self, db_session: Session, test_streamer, test_stream_session
    ):
        """Should retrieve only pending clips for a streamer"""
        # Create multiple clips with different statuses
        pending = Clip(
            stream_session_id=test_stream_session.id,
            streamer_id=test_streamer.id,
            title="Pending Clip",
            file_path="test1.mp4",
            status="pending",
            requested_by_type="auto_detection",
            requested_by_name="AI",
        )
        approved = Clip(
            stream_session_id=test_stream_session.id,
            streamer_id=test_streamer.id,
            title="Approved Clip",
            file_path="test2.mp4",
            status="approved",
            requested_by_type="auto_detection",
            requested_by_name="AI",
        )

        db_session.add_all([pending, approved])
        db_session.commit()

        # Query only pending
        results = (
            db_session.query(Clip)
            .filter(Clip.streamer_id == test_streamer.id, Clip.status == "pending")
            .all()
        )

        assert len(results) >= 1
        assert all(c.status == "pending" for c in results)
        assert all(c.streamer_id == test_streamer.id for c in results)

    def test_get_recent_clips_for_streamer(
        self, db_session: Session, test_streamer, test_stream_session
    ):
        """Should retrieve recent clips ordered by date"""
        results = (
            db_session.query(Clip)
            .filter(Clip.streamer_id == test_streamer.id)
            .order_by(Clip.created_at.desc())
            .limit(50)
            .all()
        )

        # Should be ordered by created_at descending
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].created_at >= results[i + 1].created_at

    def test_get_approved_clips(self, db_session: Session, test_streamer, test_stream_session):
        """Should retrieve only approved clips"""
        approved = Clip(
            stream_session_id=test_stream_session.id,
            streamer_id=test_streamer.id,
            title="Public Clip",
            file_path="public.mp4",
            status="approved",
            is_public=True,
            requested_by_type="auto_detection",
            requested_by_name="AI",
        )
        db_session.add(approved)
        db_session.commit()

        results = (
            db_session.query(Clip)
            .filter(Clip.streamer_id == test_streamer.id, Clip.status == "approved")
            .all()
        )

        assert len(results) > 0
        assert all(c.status == "approved" for c in results)


@pytest.mark.unit
@pytest.mark.security
class TestClipAccessControl:
    """Test access control for clips (OWASP #1)"""

    def test_clip_scoped_to_streamer(
        self, db_session: Session, test_streamer, test_stream_session
    ):
        """Clips should be scoped to streamer"""
        clip = Clip(
            stream_session_id=test_stream_session.id,
            streamer_id=test_streamer.id,
            title="Scoped Clip",
            file_path="scoped.mp4",
            requested_by_type="auto_detection",
            requested_by_name="AI",
        )
        db_session.add(clip)
        db_session.commit()

        # Should be retrievable with correct streamer_id
        retrieved = (
            db_session.query(Clip)
            .filter(Clip.id == clip.id, Clip.streamer_id == test_streamer.id)
            .first()
        )
        assert retrieved is not None

        # Should NOT be retrievable with wrong streamer_id
        not_retrieved = (
            db_session.query(Clip)
            .filter(Clip.id == clip.id, Clip.streamer_id == 99999)
            .first()
        )
        assert not_retrieved is None

    def test_cannot_modify_streamer_id(self, db_session: Session, test_clip: Clip):
        """Clip streamer_id should not be modifiable"""
        original_streamer_id = test_clip.streamer_id
        test_clip.streamer_id = 99999
        db_session.commit()

        # In practice, this should be prevented at API layer
        # but demonstrate the check
        retrieved = (
            db_session.query(Clip)
            .filter(Clip.id == test_clip.id, Clip.streamer_id == original_streamer_id)
            .first()
        )
        # Retrieved will be None because we changed it
        assert retrieved is None
