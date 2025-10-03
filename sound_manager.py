"""
Sound Management Module for Chess Game

This module handles all audio functionality including sound initialization,
creation, and playback for various game events.
"""

import pygame
from typing import Optional
from config import AudioConfig


class SoundManager:
    """Manages all sound effects for the chess game"""

    def __init__(self):
        """Initialize the sound manager and pygame mixer"""
        self.error_sound: Optional[pygame.mixer.Sound] = None

        self._initialize_mixer()
        self._create_sounds()

    def _initialize_mixer(self) -> None:
        """Initialize pygame mixer for sounds"""
        try:
            pygame.mixer.init(
                frequency=AudioConfig.FREQUENCY,
                size=AudioConfig.SIZE,
                channels=AudioConfig.CHANNELS,
                buffer=AudioConfig.BUFFER
            )
            # Audio system initialized successfully
        except pygame.error as e:
            # Failed to initialize audio system
            pass

    def _create_sounds(self) -> None:
        """Create all game sounds"""
        self.error_sound = self._create_error_sound()

    def _create_error_sound(self) -> Optional[pygame.mixer.Sound]:
        """Create a simple error beep sound using pygame"""
        try:
            import numpy as np
            sample_rate = AudioConfig.FREQUENCY
            duration = AudioConfig.BEEP_DURATION / 1000.0  # Convert to seconds
            frequency = AudioConfig.BEEP_FREQUENCY
            fade_duration = AudioConfig.FADE_DURATION

            # Generate beep sound
            frames = int(duration * sample_rate)
            arr = np.zeros(frames)

            for i in range(frames):
                # Fade in/out to avoid clicks
                fade_frames = int(fade_duration * sample_rate)
                if i < fade_frames:
                    fade = i / fade_frames
                elif i > frames - fade_frames:
                    fade = (frames - i) / fade_frames
                else:
                    fade = 1.0

                arr[i] = fade * np.sin(2 * np.pi * frequency * i / sample_rate)

            # Convert to 16-bit integers
            arr = (arr * 32767).astype(np.int16)

            # Create stereo array
            stereo_arr = np.zeros((frames, 2), dtype=np.int16)
            stereo_arr[:, 0] = arr
            stereo_arr[:, 1] = arr

            return pygame.sndarray.make_sound(stereo_arr)

        except ImportError:
            # NumPy not available for pygame sound generation
            return None
        except Exception as e:
            # Could not create pygame sound
            return None

    def _play_system_beep(self) -> None:
        """Play system beep as fallback when pygame sound isn't available"""
        try:
            import winsound
            winsound.Beep(AudioConfig.BEEP_FREQUENCY, AudioConfig.BEEP_DURATION)
        except ImportError:
            # System beep not available on this platform
            pass
        except Exception as e:
            # Failed to play system beep
            pass

    def play_error_sound(self) -> None:
        """Play error sound for invalid actions (undo/redo failures, etc.)"""
        if self.error_sound:
            try:
                self.error_sound.play()
            except pygame.error as e:
                # Failed to play error sound
                self._play_system_beep()
        else:
            self._play_system_beep()


    def cleanup(self) -> None:
        """Clean up sound resources"""
        try:
            pygame.mixer.quit()
        except pygame.error:
            pass


# Global sound manager instance
_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """Get the global sound manager instance"""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager


