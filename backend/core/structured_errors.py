"""
Structured 403 Forbidden error responses.
Provides clear feature tier and upgrade information to users.
"""

from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional, List


class UpgradeInfo(BaseModel):
    """Information about upgrading to access a feature"""
    feature_name: str
    current_tier: str
    required_tier: str
    upgrade_url: Optional[str] = None
    benefits: Optional[List[str]] = None


class StructuredForbiddenError(HTTPException):
    """
    Enhanced 403 error with feature tier information.
    
    Provides users with:
    - Feature name that was denied
    - Their current tier
    - Required tier to access feature
    - Upgrade link and benefits
    """

    def __init__(
        self,
        feature_name: str,
        current_tier: str,
        required_tier: str,
        upgrade_url: Optional[str] = None,
        benefits: Optional[List[str]] = None,
        detail: Optional[str] = None,
    ):
        self.feature_name = feature_name
        self.current_tier = current_tier
        self.required_tier = required_tier
        self.upgrade_url = upgrade_url or "/upgrade"
        self.benefits = benefits or []

        # Build detail message if not provided
        if not detail:
            detail = f"Feature '{feature_name}' requires {required_tier} tier (you have {current_tier})"

        super().__init__(status_code=403, detail=detail)

        # Attach structured error data
        self.structured_error = {
            "status": "forbidden",
            "feature_name": feature_name,
            "current_tier": current_tier,
            "required_tier": required_tier,
            "upgrade_url": self.upgrade_url,
            "benefits": self.benefits,
        }


# ==================== COMMON 403 ERRORS ====================


def forbidden_irl_mode(current_tier: str):
    """IRL streaming mode requires higher tier"""
    return StructuredForbiddenError(
        feature_name="IRL Safety Mode",
        current_tier=current_tier,
        required_tier="Professional",
        upgrade_url="/pricing?plan=professional",
        benefits=[
            "Real-time danger phrase detection",
            "Custom voice fingerprints",
            "Automated safety scenes",
            "Live transcription",
        ],
    )


def forbidden_custom_danger_phrases(current_tier: str):
    """Custom danger phrases require higher tier"""
    return StructuredForbiddenError(
        feature_name="Custom Danger Phrases",
        current_tier=current_tier,
        required_tier="Professional",
        upgrade_url="/pricing?plan=professional",
        benefits=[
            "Create custom safety triggers",
            "Adjust sensitivity per phrase",
            "Unlimited phrase library",
        ],
    )


def forbidden_voice_fingerprint(current_tier: str):
    """Voice fingerprinting requires higher tier"""
    return StructuredForbiddenError(
        feature_name="Voice Fingerprinting",
        current_tier=current_tier,
        required_tier="Professional",
        upgrade_url="/pricing?plan=professional",
        benefits=[
            "Streamer voice detection",
            "Filter non-streamer audio",
            "Reduced API costs",
        ],
    )


def forbidden_advanced_analytics(current_tier: str):
    """Advanced analytics require higher tier"""
    return StructuredForbiddenError(
        feature_name="Advanced Analytics",
        current_tier=current_tier,
        required_tier="Studio",
        upgrade_url="/pricing?plan=studio",
        benefits=[
            "Detailed viewer metrics",
            "Clip performance analytics",
            "Engagement heatmaps",
            "Revenue insights",
        ],
    )


def forbidden_team_features(current_tier: str):
    """Team/collaborative features require higher tier"""
    return StructuredForbiddenError(
        feature_name="Team Management",
        current_tier=current_tier,
        required_tier="Studio",
        upgrade_url="/pricing?plan=studio",
        benefits=[
            "Team member invites",
            "Role-based permissions",
            "Shared settings",
            "Team analytics",
        ],
    )


def forbidden_ai_features(current_tier: str):
    """AI enhancement features require higher tier"""
    return StructuredForbiddenError(
        feature_name="AI Enhancement",
        current_tier=current_tier,
        required_tier="Premium",
        upgrade_url="/pricing?plan=premium",
        benefits=[
            "AI clip suggestions",
            "Automated highlights",
            "Sentiment analysis",
            "Smart scene switching",
        ],
    )


# ==================== GENERIC HELPER ====================


def forbidden_feature(
    feature_name: str,
    current_tier: str,
    required_tier: str,
    benefits: Optional[List[str]] = None,
    upgrade_url: Optional[str] = None,
):
    """Generic 403 error for any feature tier restriction"""
    return StructuredForbiddenError(
        feature_name=feature_name,
        current_tier=current_tier,
        required_tier=required_tier,
        upgrade_url=upgrade_url,
        benefits=benefits,
    )
