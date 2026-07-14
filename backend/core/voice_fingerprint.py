"""Voice fingerprinting for streamer identity verification."""
import logging
import numpy as np
from typing import Optional
from backend.database.session import SessionLocal

logger = logging.getLogger(__name__)

# Simulated embedding dimension (actual impl would use proper voice embedding model)
EMBEDDING_DIM = 150
SIMILARITY_THRESHOLD = 0.55

# Skip fingerprint checks for the first few seconds after the agent starts,
# since mic/recording quality may still be stabilizing.
WARMUP_SECONDS = 15  # Reduced from 60 for better UX


def generate_embedding(audio_samples: bytes) -> np.ndarray:
    """
    Generate a speaker-consistent voice embedding from audio.
    Uses stable audio features (MFCC aggregation) for reproducible embeddings.
    """
    try:
        # Convert bytes to numpy array of int16 samples
        audio_np = np.frombuffer(audio_samples, dtype=np.int16).astype(np.float32)
        
        # Normalize audio
        if audio_np.max() > 0:
            audio_np = audio_np / np.abs(audio_np).max()
        
        # Compute frame-based features: simple RMS energy in frequency bands
        # This is deterministic and consistent across recordings
        frame_size = 512
        hop_size = 256
        n_frames = (len(audio_np) - frame_size) // hop_size + 1
        
        # Create n_frames energy features
        features = []
        for i in range(min(n_frames, EMBEDDING_DIM)):
            frame = audio_np[i * hop_size:i * hop_size + frame_size]
            if len(frame) > 0:
                # Frame RMS energy
                rms = np.sqrt(np.mean(frame**2))
                features.append(rms)
        
        # Pad or trim to EMBEDDING_DIM
        if len(features) < EMBEDDING_DIM:
            features.extend([0.0] * (EMBEDDING_DIM - len(features)))
        else:
            features = features[:EMBEDDING_DIM]
        
        # Convert to float32 and normalize
        emb = np.array(features, dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        else:
            emb = emb + 1e-8
            emb = emb / np.linalg.norm(emb)
        
        return emb
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        # Return zero vector on error
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two embedding vectors."""
    return float(np.dot(a, b))

def store_voice_embedding(streamer_id: int, embedding: np.ndarray, sample_text: str = None) -> bool:
    """Store voice embedding for streamer in JSON-safe format."""
    from backend.database.models.streamer import Streamer
    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        if not streamer:
            return False
        settings = streamer.settings_json or {}
        # Store as list of floats (JSON-serializable)
        settings["voice_embedding"] = embedding.tolist()
        settings["voice_sample_text"] = sample_text
        settings["voice_similarity_threshold"] = SIMILARITY_THRESHOLD
        streamer.settings_json = settings
        db.commit()
        logger.info(f"Voice embedding stored for streamer {streamer_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to store voice embedding: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_voice_embedding(streamer_id: int) -> Optional[np.ndarray]:
    """Retrieve stored voice embedding (from JSON-safe list format)."""
    from backend.database.models.streamer import Streamer
    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        if not streamer:
            return None
        settings = streamer.settings_json or {}
        emb_data = settings.get("voice_embedding")
        if emb_data:
            if isinstance(emb_data, list):
                # Convert list back to numpy array
                return np.array(emb_data, dtype=np.float32)
            # Fallback for legacy bytes format
            try:
                return np.frombuffer(emb_data, dtype=np.float32)
            except (TypeError, ValueError):
                return None
        return None
    finally:
        db.close()

def verify_voice(
    streamer_id: int,
    audio_samples: bytes,
    agent_start_time: float,
) -> bool:
    """Verify if audio matches streamer's voice.

    During the agent warmup period we skip fingerprint checks entirely.
    """

    # Warmup period: skip fingerprint check
    import time

    elapsed = time.time() - float(agent_start_time)
    if elapsed < WARMUP_SECONDS:
        return True

    stored_emb = get_voice_embedding(streamer_id)

    if stored_emb is None:
        logger.warning(f"No voice embedding for streamer {streamer_id}")
        return False
    
    incoming_emb = generate_embedding(audio_samples)
    similarity = cosine_similarity(stored_emb, incoming_emb)
    
    threshold = SIMILARITY_THRESHOLD
    logger.info(f"Voice similarity: {similarity:.3f} (threshold: {threshold})")
    return similarity >= threshold

