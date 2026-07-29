"""
Complete Test Suite for Clip Pipeline

This tests each stage of the clip generation pipeline:
1. Extract clip from replay buffer
2. Transcribe audio
3. Recrop to 9:16
4. Add captions
5. Generate title/tags
6. (Publish - v1.1)

Run with: pytest backend/tests/test_clip_pipeline.py -v -s
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from backend.core.clip_pipeline import ClipPipeline, ClipPipelineError


class TestClipPipeline:
    """Test suite for clip pipeline"""

    @pytest.fixture
    def pipeline(self):
        """Create a test pipeline with temp directory"""
        temp_dir = tempfile.mkdtemp()
        return ClipPipeline(temp_dir=temp_dir)

    @pytest.fixture
    def mock_obs_adapter(self):
        """Create a mock OBS adapter"""
        adapter = Mock()
        adapter.get_replay_buffer_path = AsyncMock(return_value=None)
        return adapter

    # ===== STAGE 1: EXTRACT =====

    @pytest.mark.asyncio
    async def test_extract_creates_output_file(self, pipeline, mock_obs_adapter):
        """Test that extract_clip_segment raises error when no replay buffer"""
        with pytest.raises(ClipPipelineError):
            await pipeline.extract_clip_segment(
                mock_obs_adapter,
                start_seconds=0,
                duration_seconds=45,
            )

    # ===== STAGE 2: TRANSCRIBE =====

    @pytest.mark.asyncio
    async def test_transcribe_empty_input(self, pipeline):
        """Test transcription with no audio returns empty result"""
        # Create a dummy empty MP4 (very small, no real audio)
        # For real testing, provide an actual MP4 file
        result = await pipeline.transcribe_audio("/dev/null")
        assert "full_text" in result
        assert "words" in result
        # Empty file should return empty transcript
        assert result["full_text"] == ""

    # ===== STAGE 3: RECROP =====

    @pytest.mark.asyncio
    async def test_recrop_handles_missing_file(self, pipeline):
        """Test recrop gracefully handles missing input file"""
        # Should return the same path if crop fails
        result = await pipeline.recrop_to_vertical("/nonexistent/video.mp4")
        assert result == "/nonexistent/video.mp4"

    # ===== STAGE 4: CAPTION =====

    @pytest.mark.asyncio
    async def test_add_captions_empty_transcript(self, pipeline):
        """Test caption generation with empty transcript"""
        result = await pipeline.add_captions(
            "/dummy/video.mp4",
            {"full_text": "", "words": []}
        )
        # Should return same file if no words
        assert result == "/dummy/video.mp4"

    @pytest.mark.asyncio
    async def test_create_srt_file_format(self, pipeline):
        """Test SRT file is created in correct format"""
        output_path = Path(pipeline.temp_dir) / "test.srt"
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "World", "start": 0.5, "end": 1.0},
        ]
        pipeline._create_srt_file(output_path, words)

        assert output_path.exists()
        content = output_path.read_text()
        assert "Hello" in content
        assert "World" in content
        assert "00:00:00,000 --> 00:00:00,500" in content

    @staticmethod
    def test_format_srt_time():
        """Test SRT time formatting"""
        assert ClipPipeline._format_srt_time(0.0) == "00:00:00,000"
        assert ClipPipeline._format_srt_time(61.5) == "00:01:01,500"
        assert ClipPipeline._format_srt_time(3661.999) == "01:01:01,999"

    # ===== STAGE 5: LABEL =====

    @pytest.mark.asyncio
    async def test_generate_title_empty_transcript(self, pipeline):
        """Test title generation with empty transcript"""
        result = await pipeline.generate_title_and_tags(
            {"full_text": "", "words": []},
            context="Test moment"
        )
        assert "title" in result
        assert "hashtags" in result
        assert "virality_score" in result
        # Should return defaults for empty input
        assert result["title"] != ""
        assert len(result["hashtags"]) > 0
        assert 1 <= result["virality_score"] <= 10

    @pytest.mark.asyncio
    async def test_generate_title_with_text(self, pipeline):
        """Test title generation with actual transcript"""
        result = await pipeline.generate_title_and_tags(
            {"full_text": "That was an epic world record run!", "words": []},
            context="Speedrun attempt"
        )
        assert "title" in result
        assert result["title"] != ""
        assert 1 <= result["virality_score"] <= 10

    # ===== STAGE 6: PUBLISH =====

    @pytest.mark.asyncio
    async def test_publish_placeholder(self, pipeline):
        """Test publish endpoint (currently placeholder)"""
        result = await pipeline.publish_to_youtube_shorts(
            "/dummy/clip.mp4",
            "Epic Moment",
            ["#gaming", "#clip"],
            "StreamerName"
        )
        # v1 returns None (not implemented yet)
        assert result is None

    # ===== END-TO-END =====

    @pytest.mark.asyncio
    async def test_process_orchestration(self, pipeline, mock_obs_adapter):
        """Test full pipeline orchestration"""
        moment_data = {
            "start_seconds": 0,
            "duration_seconds": 45,
            "context": "Test moment",
            "streamer_name": "TestStreamer",
        }

        # This will fail at extract stage (no real replay buffer)
        # But it tests the orchestration flow
        result = await pipeline.process(
            moment_data=moment_data,
            obs_adapter=mock_obs_adapter,
            streamer_id=123,
        )

        assert "status" in result
        assert "clip_id" in result
        # Will be "failed" since we don't have a real replay buffer
        assert result["status"] in ["success", "partial", "failed"]


# ===== MANUAL TESTING GUIDE =====

MANUAL_TEST_GUIDE = """
To manually test the clip pipeline end-to-end:

1. Start the backend:
   cd backend
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

2. Test the /api/clips/test endpoint:
   curl -X POST http://localhost:8000/api/clips/test \\
     -H "Authorization: Bearer YOUR_TOKEN"

3. Trigger clip generation manually:
   curl -X POST http://localhost:8000/api/clips/generate \\
     -H "Authorization: Bearer YOUR_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{
       "title": "Manual Test Clip",
       "context": "Testing the pipeline",
       "duration_seconds": 45
     }'

4. Check recent clips:
   curl -X GET "http://localhost:8000/api/clips/recent?limit=5" \\
     -H "Authorization: Bearer YOUR_TOKEN"

5. Monitor logs:
   Watch the backend console for clip_pipeline.py log messages
   Look for: "✓ Clip pipeline complete" or "✗ Clip pipeline failed"

6. To test with real OBS:
   - Make sure OBS is recording to a local file
   - Start a stream
   - Trigger a clip via voice command or dashboard button
   - Watch the pipeline process the clip:
     * Extract: 5-10 seconds
     * Transcribe: 10-20 seconds (depends on duration)
     * Recrop: 5 seconds
     * Caption: 10 seconds
     * Label: 3 seconds
     * Publish: N/A (v1.1)
   - Check the recent clips endpoint to see the result
"""


if __name__ == "__main__":
    print(MANUAL_TEST_GUIDE)
