"""
Audio feedback system for command confirmations.
Plays brief confirmation sounds (< 1 second) after successful command execution.
"""
import os
import asyncio
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioFeedback:
    """Manages audio playback for command confirmations."""
    
    def __init__(self):
        self.audio_dir = Path(__file__).parent.parent / "assets" / "sounds"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._sound_cache = {}
    
    def _ensure_sound_files_exist(self):
        """Create placeholder audio files if they don't exist."""
        sounds = {
            "command_success.wav": b"RIFF\x24\x00\x00\x00WAVE",  # Minimal WAV header for success
            "scene_switch.wav": b"RIFF\x24\x00\x00\x00WAVE",     # Scene switch sound
            "clip_saved.wav": b"RIFF\x24\x00\x00\x00WAVE",       # Clip saved sound
            "error.wav": b"RIFF\x24\x00\x00\x00WAVE",            # Error sound
        }
        
        for filename, header in sounds.items():
            filepath = self.audio_dir / filename
            if not filepath.exists():
                try:
                    filepath.write_bytes(header)
                    logger.info(f"Created placeholder sound file: {filepath}")
                except Exception as e:
                    logger.warning(f"Could not create sound file {filename}: {e}")
    
    async def play_success(self, command: str = "command_success"):
        """Play success confirmation sound for a command."""
        await self.play_sound(command)
    
    async def play_sound(self, sound_name: str):
        """
        Play audio file asynchronously.
        Sound files should be stored in backend/assets/sounds/
        """
        try:
            sound_path = self.audio_dir / f"{sound_name}.wav"
            
            if not sound_path.exists():
                logger.debug(f"Sound file not found: {sound_path}, skipping playback")
                return
            
            # Try to play using system audio
            await self._play_system_audio(str(sound_path))
        
        except Exception as e:
            logger.warning(f"Failed to play sound {sound_name}: {e}")
    
    async def _play_system_audio(self, filepath: str):
        """Play audio using system player (platform-specific)."""
        try:
            import platform
            import subprocess
            
            system = platform.system()
            
            if system == "Windows":
                # Use PowerShell with param block to safely pass filepath
                proc = await asyncio.create_subprocess_exec(
                    "powershell", "-NoProfile", "-Command",
                    "param($p); (New-Object System.Media.SoundPlayer($p)).PlaySync()",
                    filepath,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            elif system == "Darwin":
                # macOS: use afplay
                proc = await asyncio.create_subprocess_exec(
                    "afplay", filepath,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            else:
                # Linux: try paplay, aplay, or ffplay
                proc = await asyncio.create_subprocess_exec(
                    "paplay", filepath,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
        
        except Exception as e:
            logger.debug(f"System audio playback failed: {e}")


# Global instance
_audio_feedback = AudioFeedback()
_audio_feedback._ensure_sound_files_exist()


async def play_command_feedback(command: str):
    """
    Play audio feedback for a successfully executed command.
    Called after command execution completes.
    
    Args:
        command: The command name (e.g., "switch_scene", "mute_mic", "create_clip")
    """
    sound_map = {
        "switch_scene": "scene_switch",
        "toggle_camera": "command_success",
        "set_source_visibility": "command_success",
        "switch_camera_device": "command_success",
        "mute_mic": "command_success",
        "unmute_mic": "command_success",
        "set_audio_level": "command_success",
        "start_recording": "command_success",
        "stop_recording": "command_success",
        "start_streaming": "command_success",
        "stop_streaming": "command_success",
        "create_clip": "clip_saved",
        "save_replay_buffer": "clip_saved",
    }
    
    sound_name = sound_map.get(command, "command_success")
    await _audio_feedback.play_sound(sound_name)
