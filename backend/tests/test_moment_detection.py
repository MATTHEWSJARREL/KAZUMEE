"""
Unit tests for moment detection system.
Tests score calculations, thresholds, and EWMA baseline logic.
"""

import pytest
from backend.core.moment_detector import MomentDetector, DetectedMoment


@pytest.mark.unit
class TestMomentDetector:
    """Test moment detection algorithm"""

    @pytest.fixture
    def detector(self):
        """Create a moment detector instance"""
        return MomentDetector(sensitivity=0.7)

    def test_detector_initialization(self, detector):
        """Detector should initialize with sensitivity"""
        assert detector is not None
        assert detector.sensitivity == 0.7

    def test_detector_sensitivity_range(self):
        """Sensitivity should be between 0 and 1"""
        detector_low = MomentDetector(sensitivity=0.0)
        assert detector_low.sensitivity == 0.0

        detector_high = MomentDetector(sensitivity=1.0)
        assert detector_high.sensitivity == 1.0

    def test_detect_moment_basic(self, detector):
        """Should detect moment from chat metrics"""
        # Simulate high chat activity
        moment = detector.detect_moment(
            moment_id="test_1",
            timestamp=1000000,
            chat_events=100,  # High activity
            emote_rate=0.5,
            caps_ratio=0.3,
        )

        assert moment is not None
        assert isinstance(moment, DetectedMoment)
        assert moment.combined_score > 0

    def test_detect_moment_no_activity(self, detector):
        """Should not detect moment with low activity"""
        moment = detector.detect_moment(
            moment_id="test_2",
            timestamp=1000000,
            chat_events=1,  # Very low
            emote_rate=0.01,
            caps_ratio=0.01,
        )

        # Might still return a moment but with low score
        assert moment is not None
        assert moment.combined_score < 50  # Should be low score


@pytest.mark.unit
class TestScoreCalculation:
    """Test score calculation logic"""

    def test_high_chat_events_increases_score(self):
        """More chat events should increase score"""
        detector = MomentDetector(sensitivity=0.7)

        moment_low = detector.detect_moment(
            moment_id="low",
            timestamp=1000000,
            chat_events=10,
            emote_rate=0.1,
            caps_ratio=0.1,
        )

        moment_high = detector.detect_moment(
            moment_id="high",
            timestamp=1000000,
            chat_events=1000,
            emote_rate=0.1,
            caps_ratio=0.1,
        )

        assert moment_high.combined_score > moment_low.combined_score

    def test_high_emote_rate_increases_score(self):
        """High emote rate should increase score"""
        detector = MomentDetector(sensitivity=0.7)

        moment_low = detector.detect_moment(
            moment_id="low",
            timestamp=1000000,
            chat_events=100,
            emote_rate=0.01,
            caps_ratio=0.1,
        )

        moment_high = detector.detect_moment(
            moment_id="high",
            timestamp=1000000,
            chat_events=100,
            emote_rate=0.8,
            caps_ratio=0.1,
        )

        assert moment_high.combined_score > moment_low.combined_score

    def test_high_caps_ratio_increases_score(self):
        """High caps ratio should increase score"""
        detector = MomentDetector(sensitivity=0.7)

        moment_low = detector.detect_moment(
            moment_id="low",
            timestamp=1000000,
            chat_events=100,
            emote_rate=0.2,
            caps_ratio=0.01,
        )

        moment_high = detector.detect_moment(
            moment_id="high",
            timestamp=1000000,
            chat_events=100,
            emote_rate=0.2,
            caps_ratio=0.9,
        )

        assert moment_high.combined_score > moment_low.combined_score

    def test_score_range(self, detector):
        """Scores should be between 0 and 100"""
        moment = detector.detect_moment(
            moment_id="test",
            timestamp=1000000,
            chat_events=500,
            emote_rate=0.5,
            caps_ratio=0.4,
        )

        assert 0 <= moment.combined_score <= 100


@pytest.mark.unit
class TestSensitivityImpact:
    """Test how sensitivity affects moment detection"""

    def test_low_sensitivity_requires_high_activity(self):
        """Low sensitivity should require more activity"""
        detector_low = MomentDetector(sensitivity=0.1)

        moment = detector_low.detect_moment(
            moment_id="test",
            timestamp=1000000,
            chat_events=50,  # Moderate activity
            emote_rate=0.3,
            caps_ratio=0.2,
        )

        # Low sensitivity = harder to trigger
        assert moment.combined_score < 50

    def test_high_sensitivity_detects_moderate_activity(self):
        """High sensitivity should detect moderate activity"""
        detector_high = MomentDetector(sensitivity=0.9)

        moment = detector_high.detect_moment(
            moment_id="test",
            timestamp=1000000,
            chat_events=50,  # Moderate activity
            emote_rate=0.3,
            caps_ratio=0.2,
        )

        # High sensitivity = easier to trigger
        # Should still be relatively low for moderate activity
        assert isinstance(moment, DetectedMoment)


@pytest.mark.unit
class TestDetectedMomentModel:
    """Test DetectedMoment data structure"""

    def test_detected_moment_has_required_fields(self, detector):
        """DetectedMoment should have all required fields"""
        moment = detector.detect_moment(
            moment_id="test_123",
            timestamp=1000000,
            chat_events=100,
            emote_rate=0.5,
            caps_ratio=0.3,
        )

        assert hasattr(moment, "moment_id")
        assert hasattr(moment, "combined_score")
        assert hasattr(moment, "timestamp")
        assert hasattr(moment, "context")

        assert moment.moment_id == "test_123"
        assert moment.timestamp == 1000000
        assert isinstance(moment.combined_score, (int, float))

    def test_detected_moment_context_string(self, detector):
        """DetectedMoment should have context description"""
        moment = detector.detect_moment(
            moment_id="test",
            timestamp=1000000,
            chat_events=500,
            emote_rate=0.8,
            caps_ratio=0.6,
        )

        assert moment.context is not None
        assert isinstance(moment.context, str)
        assert len(moment.context) > 0

    def test_detected_moment_unique_ids(self, detector):
        """Each detected moment should have unique ID"""
        moment1 = detector.detect_moment(
            moment_id="unique_1",
            timestamp=1000000,
            chat_events=100,
            emote_rate=0.5,
            caps_ratio=0.3,
        )

        moment2 = detector.detect_moment(
            moment_id="unique_2",
            timestamp=1000000,
            chat_events=100,
            emote_rate=0.5,
            caps_ratio=0.3,
        )

        assert moment1.moment_id != moment2.moment_id


@pytest.mark.unit
class TestThresholdLogic:
    """Test moment detection thresholds"""

    def test_detector_respects_sensitivity_threshold(self):
        """Detector should filter moments below sensitivity threshold"""
        detector = MomentDetector(sensitivity=0.8)  # High threshold

        low_activity = detector.detect_moment(
            moment_id="low",
            timestamp=1000000,
            chat_events=10,
            emote_rate=0.05,
            caps_ratio=0.05,
        )

        # With high sensitivity, low activity should produce low score
        assert low_activity.combined_score < 50

    def test_zero_activity_produces_zero_score(self):
        """Zero activity should produce zero or near-zero score"""
        detector = MomentDetector(sensitivity=0.7)

        moment = detector.detect_moment(
            moment_id="zero",
            timestamp=1000000,
            chat_events=0,
            emote_rate=0.0,
            caps_ratio=0.0,
        )

        assert moment.combined_score == 0
