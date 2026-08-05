"""
Clip Generator Service

Triggered by moment detection, actually extracts and processes video clips
using the ClipPipeline. Replaces simple DB inserts with full video generation.
"""

import asyncio
import logging
import time
import os
import json
import traceback
from datetime import datetime
from typing import Optional

from backend.core.clip_pipeline import ClipPipeline, ClipPipelineError
from backend.core.moment_detector import DetectedMoment
from backend.database.session import SessionLocal
from backend.database.models.clip import Clip
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ClipGeneratorService:
    """Generates actual video clips from detected moments"""

    def __init__(self, obs_adapter, pipeline: Optional[ClipPipeline] = None):
        """
        Initialize clip generator.

        Args:
            obs_adapter: OBS WebSocket adapter for replay buffer access
            pipeline: ClipPipeline instance (creates new if None)
        """
        self.obs_adapter = obs_adapter
        self.pipeline = pipeline or ClipPipeline()
        self.is_processing = False
        logger.info("Clip Generator Service initialized")

    def on_moment_detected(self, moment: DetectedMoment):
        """Callback when moment is detected"""
        logger.warning(f"🎬 TRIGGER FIRED: moment_id={moment.moment_id} score={moment.combined_score:.2f}")

        if self.is_processing:
            logger.warning(f"Skipping (already processing)")
            return

        self.is_processing = True
        try:
            # Create clip record
            self._create_clip_record(moment)
            logger.warning(f"✅ CLIP CREATED from moment")
        except Exception as e:
            logger.error(f"❌ Clip creation failed: {traceback.format_exc()}")
        finally:
            self.is_processing = False

    def _create_clip_record(self, moment: DetectedMoment):
        """Create a clip record in the database from a detected moment with video extraction"""
        from backend.core.logger import log_event, EventType

        db = None
        start_time = time.time()
        clip_id = None

        try:
            from backend.database.session import SessionLocal
            from sqlalchemy import text
            from backend.core.video_extractor import get_extractor

            db = SessionLocal()
            streamer_id = moment.streamer_id  # From detected moment (REQUIRED)

            # Log clip detection
            log_event(
                EventType.CLIP_DETECTED,
                str(streamer_id),
                f"Moment detected (score: {moment.combined_score:.1f})",
                metadata={"moment_id": moment.moment_id, "context": moment.context[:50]}
            )

            # Step 1: Extract video from OBS replay buffer or fallback source
            logger.info(f"Extracting video for moment {moment.moment_id}...")
            log_event(
                EventType.EXTRACTION_STARTED,
                str(streamer_id),
                f"Video extraction started for moment {moment.moment_id}"
            )

            extractor = get_extractor()
            video_source = None

            # Try OBS replay buffer first
            if self.obs_adapter:
                try:
                    replay_path = self.obs_adapter.get_replay_buffer_status()
                    if replay_path and os.path.exists(replay_path):
                        video_source = replay_path
                        logger.info(f"Using OBS replay buffer: {video_source}")
                except Exception as e:
                    logger.warning(f"Could not access OBS replay buffer: {e}")

            # Fall back to test video if OBS not available
            if not video_source:
                fallback_video = "backend/data/test_videos/test_stream.mp4"
                if os.path.exists(fallback_video):
                    video_source = fallback_video
                    logger.info(f"Using fallback video: {video_source}")
                else:
                    logger.error("No video source available (OBS not connected and no fallback video)")
                    log_event(
                        EventType.EXTRACTION_FAILED,
                        str(streamer_id),
                        "No video source available",
                        error="OBS not connected and no fallback video"
                    )
                    return

            # Step 2: Extract the video segment (45 seconds)
            file_path = extractor.extract_segment(
                input_video=video_source,
                start_seconds=0,
                duration_seconds=45
            )

            if not file_path:
                logger.error(f"Failed to extract video segment for moment {moment.moment_id}")
                log_event(
                    EventType.EXTRACTION_FAILED,
                    str(streamer_id),
                    f"Video extraction failed for moment {moment.moment_id}",
                    error="FFmpeg extraction returned no file path"
                )
                return

            extraction_time = int((time.time() - start_time) * 1000)
            logger.info(f"✅ Video extracted: {file_path}")
            log_event(
                EventType.EXTRACTION_SUCCEEDED,
                str(streamer_id),
                f"Video extracted successfully ({extraction_time}ms)",
                duration_ms=extraction_time,
                metadata={"file_path": file_path}
            )

            # Step 3: Create clip record with actual file path
            title = "AUTO CLIP"
            score = min(moment.combined_score / 100, 1.0)

            query = text("""
                INSERT INTO clips (title, description, file_path, status,
                                  requested_by_type, requested_by_name,
                                  duration_seconds, quality_score,
                                  stream_session_id, streamer_id, created_at)
                VALUES (:title, :desc, :file_path, :status,
                       :req_type, :req_name, :dur, :score,
                       :session_id, :streamer_id, NOW())
                RETURNING id
            """)
            result = db.execute(query, {
                "title": title,
                "desc": moment.context[:100] if moment.context else "Auto moment",
                "file_path": file_path,
                "status": "pending",
                "req_type": "auto_detection",
                "req_name": "AI",
                "dur": 45,
                "score": score,
                "session_id": 1,
                "streamer_id": streamer_id
            })

            # Get the clip ID
            try:
                clip_id = result.scalar()
            except:
                pass

            db.commit()
            total_time = int((time.time() - start_time) * 1000)
            logger.warning(f"✅ CLIP CREATED in DB (score={score:.2f}) → {file_path}")

            log_event(
                EventType.EXTRACTION_SUCCEEDED,
                str(streamer_id),
                f"Clip created successfully (ID: {clip_id})",
                clip_id=clip_id,
                duration_ms=total_time,
                metadata={"title": title, "score": score}
            )

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"❌ Clip creation failed: {type(e).__name__}: {e}", exc_info=True)

            log_event(
                EventType.EXTRACTION_FAILED,
                str(1),
                f"Clip creation exception",
                clip_id=clip_id,
                error=f"{type(e).__name__}: {str(e)[:100]}"
            )
            raise
        finally:
            if db:
                db.close()

    async def _old_on_moment_detected_with_video_extraction(self, moment: DetectedMoment):
        """OLD: Callback with video extraction (keeping for reference)"""
        try:
            print(f"[CLIP_GEN] Callback invoked for moment {moment.moment_id}")
        except:
            pass
        logger.info(f"[CLIP] Generating clip for moment: {moment.moment_id}")

        if self.is_processing:
            logger.info(f"Skipping moment (processing already in progress)")
            return

        self.is_processing = True
        try:
            logger.info(f"Starting clip generation...")

            # Extract clip from video source (OBS replay buffer or test video)
            from backend.core.video_extractor import get_extractor

            extractor = get_extractor()

            # Try to get replay buffer from OBS, fall back to test video
            video_source = "backend/data/test_videos/test_stream.mp4"

            try:
                replay_path = await self.obs_adapter.get_replay_buffer_path()
                if replay_path and os.path.exists(replay_path):
                    video_source = replay_path
                    logger.info(f"Using OBS replay buffer: {video_source}")
            except Exception as e:
                logger.warning(f"OBS replay buffer not available, using test video: {e}")

            # Extract 45-second clip
            clip_path = extractor.extract_segment(
                input_video=video_source,
                start_seconds=0,
                duration_seconds=45
            )

            if not clip_path:
                logger.error("Failed to extract clip video")
                return

            logger.info(f"[OK] Extracted clip: {clip_path}")

            # TODO: Crop to vertical (9:16) format (stage 3)
            # For now, skip vertical cropping - will implement later

            # Transcribe audio
            logger.info("Transcribing audio...")
            original_clip_path = clip_path  # Keep original for caption burning
            print(f"[DEBUG] About to transcribe: {clip_path}")
            transcript = None
            try:
                from backend.core.transcriber import get_transcriber

                transcriber = get_transcriber()
                print(f"[DEBUG] Transcriber loaded")
                transcript = transcriber.transcribe(clip_path)
                print(f"[DEBUG] Transcription result: {transcript}")

                if transcript:
                    print(f"[DEBUG] Transcript text: {transcript.text[:50]}")
                    print(f"[DEBUG] Transcript words: {len(transcript.words)}")
                    logger.info(f"[OK] Transcribed: {len(transcript.words)} words")
                else:
                    print("[DEBUG] Transcription returned None")
                    logger.warning("Transcription returned None")
            except Exception as e:
                print(f"[DEBUG] Transcription exception: {e}")
                logger.error(f"Transcription error: {e}", exc_info=True)

            # TODO: Burn captions onto video (stage 4)
            # For now, skip FFmpeg caption processing - captions stored in content_analysis

            # Determine title based on score
            title_map = {
                (80, 100): "EPIC MOMENT",
                (60, 80): "HIGHLIGHT",
                (40, 60): "INTERESTING MOMENT",
                (0, 40): "MOMENT DETECTED",
            }

            title = "MOMENT DETECTED"
            for (low, high), title_text in title_map.items():
                if low <= moment.combined_score < high:
                    title = title_text
                    break

            # Save clip metadata to database
            db = SessionLocal()
            try:
                # Store transcription as JSON in clip metadata (always store, even if empty)
                content_analysis = {
                    "transcription": transcript.text if transcript and hasattr(transcript, 'text') else "[Transcription pending]",
                    "words": transcript.words if transcript and hasattr(transcript, 'words') else [],
                    "word_count": len(transcript.words) if transcript and hasattr(transcript, 'words') else 0,
                }

                print(f"[DEBUG] content_analysis dict: {content_analysis}")
                content_analysis_json = json.dumps(content_analysis)
                print(f"[DEBUG] content_analysis JSON: {content_analysis_json[:100]}")

                # Use streamer_id from the moment object (REQUIRED)
                streamer_id = moment.streamer_id
                streamer = db.query(text("SELECT 1 FROM streamers WHERE id = :id")).params(id=streamer_id).first()
                if not streamer:
                    # Create default streamer if it doesn't exist
                    from backend.database.models.streamer import Streamer
                    default_streamer = Streamer(id=streamer_id, username=f"streamer_{streamer_id}", display_name=f"Streamer {streamer_id}", platform="kazumi")
                    db.add(default_streamer)
                    db.flush()
                    logger.warning(f"Created default streamer record for streamer_id={streamer_id} (should have pre-existing record)")

                # Ensure stream_session exists for this streamer (for dev/testing)
                session = db.query(text("SELECT 1 FROM stream_sessions WHERE streamer_id = :streamer_id LIMIT 1")).params(streamer_id=streamer_id).first()
                if not session:
                    # Create default stream session if it doesn't exist
                    from backend.database.models.stream_session import StreamSession
                    default_session = StreamSession(id=1, streamer_id=streamer_id, status="active")
                    db.add(default_session)
                    db.flush()
                    logger.info("Created default stream session for clip storage")

                print(f"[DEBUG] Inserting clip into database...")
                db.execute(text("""
                    INSERT INTO clips (
                        title, description, file_path, status,
                        requested_by_type, requested_by_name,
                        duration_seconds, quality_score,
                        content_analysis,
                        stream_session_id, streamer_id
                    ) VALUES (
                        :title, :description, :file_path, :status,
                        :requested_by_type, :requested_by_name,
                        :duration_seconds, :quality_score,
                        :content_analysis,
                        :stream_session_id, :streamer_id
                    )
                """), {
                    "title": title,
                    "description": moment.context,
                    "file_path": clip_path,  # Actual file path!
                    "status": "pending",
                    "requested_by_type": "auto_detection",
                    "requested_by_name": "Kazumee AI",
                    "duration_seconds": 45,
                    "quality_score": min(moment.combined_score / 100, 1.0),
                    "content_analysis": content_analysis_json,  # Use pre-serialized JSON
                    "stream_session_id": 1,
                    "streamer_id": 1
                })
                print(f"[DEBUG] Execute complete, committing...")
                db.commit()
                logger.info(f"[OK] Clip recorded in DB: {title} (score: {moment.combined_score:.0f}/100, transcription: {len(transcript.words) if transcript else 0} words)")

            except Exception as e:
                logger.error(f"Failed to save clip to DB: {e}")
                db.rollback()
            finally:
                db.close()

        except ClipPipelineError as e:
            logger.error(f"[ERROR] Clip generation failed: {e}")
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error in clip generator: {e}", exc_info=True)
        finally:
            self.is_processing = False


# Global service instance
_clip_generator: Optional[ClipGeneratorService] = None


def get_clip_generator() -> Optional[ClipGeneratorService]:
    """Get global clip generator service"""
    return _clip_generator


def set_clip_generator(service: ClipGeneratorService):
    """Set global clip generator service"""
    global _clip_generator
    _clip_generator = service
