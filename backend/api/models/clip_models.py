"""
Validated Pydantic models for clip operations with security hardening.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from backend.core.security import (
    validate_clip_title,
    validate_clip_description,
    validate_clip_notes,
    validate_tags,
    ValidationError,
)


class ClipReviewRequest(BaseModel):
    """Request to approve or reject a clip"""
    clip_id: int = Field(..., gt=0, description="Clip ID must be positive")
    action: str = Field(..., description="Action: 'approve' or 'reject'")
    notes: Optional[str] = Field(None, max_length=5000, description="Optional reviewer notes")

    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ('approve', 'reject'):
            raise ValueError("Action must be 'approve' or 'reject'")
        return v

    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v):
        if v is None:
            return None
        try:
            return validate_clip_notes(v)
        except ValidationError as e:
            raise ValueError(str(e))


class ClipUpdateRequest(BaseModel):
    """Request to update clip metadata"""
    title: Optional[str] = Field(None, max_length=255, description="Clip title")
    description: Optional[str] = Field(None, max_length=2000, description="Clip description")
    notes: Optional[str] = Field(None, max_length=5000, description="Internal notes")
    tags: Optional[List[str]] = Field(None, max_items=20, description="Clip tags (max 20)")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is None:
            return None
        try:
            return validate_clip_title(v)
        except ValidationError as e:
            raise ValueError(str(e))

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v is None:
            return None
        try:
            return validate_clip_description(v)
        except ValidationError as e:
            raise ValueError(str(e))

    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v):
        if v is None:
            return None
        try:
            return validate_clip_notes(v)
        except ValidationError as e:
            raise ValueError(str(e))

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v is None:
            return None
        try:
            return validate_tags(v)
        except ValidationError as e:
            raise ValueError(str(e))


class StreamClipRequest(BaseModel):
    """Request to stream a clip"""
    clip_id: int = Field(..., gt=0, description="Clip ID must be positive")


class ClipCreateRequest(BaseModel):
    """Request to create a new clip"""
    file_path: str = Field(..., max_length=1000, description="File path to clip")
    requested_by_type: str = Field(..., max_length=50, description="Who requested the clip")
    requested_by_id: Optional[str] = Field(None, max_length=128, description="ID of requester")
    requested_by_name: Optional[str] = Field(None, max_length=128, description="Name of requester")
    title: Optional[str] = Field(None, max_length=255, description="Clip title")
    description: Optional[str] = Field(None, max_length=2000, description="Clip description")
    stream_session_id: int = Field(1, gt=0, description="Stream session ID")

    @field_validator('requested_by_type')
    @classmethod
    def validate_requested_by_type(cls, v):
        allowed = {'auto_detection', 'viewer_request', 'manual', 'system'}
        if v not in allowed:
            raise ValueError(f"requested_by_type must be one of {allowed}")
        return v

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is None:
            return None
        try:
            return validate_clip_title(v)
        except ValidationError as e:
            raise ValueError(str(e))

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v is None:
            return None
        try:
            return validate_clip_description(v)
        except ValidationError as e:
            raise ValueError(str(e))


class ClipExportRequest(BaseModel):
    """Request to export a clip"""
    preset: str = Field(..., description="Export preset")
    watermark_text: Optional[str] = Field(None, max_length=255, description="Watermark text")
    subtitles_path: Optional[str] = Field(None, max_length=1000, description="Path to subtitles")

    @field_validator('preset')
    @classmethod
    def validate_preset(cls, v):
        allowed = {'tiktok', 'shorts', 'reels', 'youtube', 'instagram'}
        if v not in allowed:
            raise ValueError(f"preset must be one of {allowed}")
        return v

    @field_validator('watermark_text')
    @classmethod
    def validate_watermark(cls, v):
        if v is None:
            return None
        if len(v) > 255:
            raise ValueError("Watermark text too long")
        return v
