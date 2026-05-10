import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# STT Engines (Speech-to-Text)
FASTER_WHISPER_AVAILABLE = False
VOSK_AVAILABLE = False
WHISPER_AVAILABLE = False

# TTS Engines (Text-to-Speech)
PIPER_AVAILABLE = False
EDGE_TTS_AVAILABLE = False
PYTTSX3_AVAILABLE = False

# Audio I/O
SOUNDDEVICE_AVAILABLE = False

# STT ENGINE IMPORTS (order: faster-whisper > vosk > whisper)
try:
    from faster_whisper import WhisperModel

    FASTER_WHISPER_AVAILABLE = True
    logger.info("STT: faster-whisper available (primary)")
except ImportError:
    WhisperModel = None

try:
    import vosk

    VOSK_AVAILABLE = True
    logger.info("STT: vosk available (fallback)")
except ImportError:
    vosk = None

try:
    import whisper

    WHISPER_AVAILABLE = True
    logger.info("STT: whisper available (fallback)")
except ImportError:
    whisper = None

STT_AVAILABLE = FASTER_WHISPER_AVAILABLE or VOSK_AVAILABLE or WHISPER_AVAILABLE

# TTS ENGINE IMPORTS (order: piper > edge-tts > pyttsx3)
try:
    import piper

    PIPER_AVAILABLE = True
    logger.info("TTS: piper available (primary)")
except ImportError:
    piper = None

try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
    logger.info("TTS: edge-tts available (fallback)")
except ImportError:
    edge_tts = None

try:
    import pyttsx3

    PYTTSX3_AVAILABLE = True
    logger.info("TTS: pyttsx3 available (fallback)")
except ImportError:
    pyttsx3 = None

TTS_AVAILABLE = PIPER_AVAILABLE or EDGE_TTS_AVAILABLE or PYTTSX3_AVAILABLE

# Audio I/O
try:
    import sounddevice as sd
    import soundfile as sf

    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    sd = None
    sf = None

# Wake word
OPENWAKEWORD_AVAILABLE = False
try:
    import openwakeword
    from openwakeword.model import Model as OWWModel

    OPENWAKEWORD_AVAILABLE = True
    logger.info("Wake word: openwakeword available (always-on listening)")
except ImportError:
    openwakeword = None
    OWWModel = None

# Cached models (lazy loaded)
_faster_whisper_model = None
_vosk_model = None
_piper_voice = None
_oww_model = None

# Wake word listener state
_wake_listener_running = False
_wake_listener_task: asyncio.Task | None = None
_wake_command_queue: asyncio.Queue | None = None
_detected_commands: list[dict[str, Any]] = []

# Built-in alarm sounds
ALARM_SOUNDS = {
    "siren": {"freq": [800, 1200], "duration": 0.5, "pattern": "alternate"},
    "beep": {"freq": [1000], "duration": 0.2, "pattern": "single"},
    "urgent": {"freq": [880, 988, 1047], "duration": 0.15, "pattern": "sequence"},
    "doorbell": {"freq": [523, 659], "duration": 0.3, "pattern": "ding_dong"},
    "chime": {"freq": [1047, 1319, 1568, 2093], "duration": 0.2, "pattern": "cascade"},
    "alarm": {"freq": [440, 880], "duration": 0.25, "pattern": "rapid"},
    "attention": {"freq": [600], "duration": 0.1, "pattern": "triple"},
    "success": {"freq": [523, 659, 784], "duration": 0.15, "pattern": "ascending"},
    "error": {"freq": [400, 300], "duration": 0.3, "pattern": "descending"},
    "alert": {"freq": [1000, 500], "duration": 0.4, "pattern": "two_tone"},
}

WAKE_WORDS = ["hey tapo", "ok tapo", "yo tapo"]

AUDIO_ACTIONS = {
    "get_url": "Get RTSP stream URL with audio for a camera",
    "capabilities": "Get audio capabilities overview (TTS, STT, alarms, etc.)",
    "player_url": "Get URL for browser audio player page",
    "vlc_command": "Get VLC command to play camera stream with audio",
    "speak": "Text-to-speech: speak a message through speakers",
    "announce": "Announcement: speak message with attention chime first",
    "listen": "Speech-to-text: listen and transcribe (requires microphone)",
    "voice_command": "Listen for voice command with wake word detection",
    "wake_start": "Start always-on wake word listener (background, offline)",
    "wake_stop": "Stop the always-on wake word listener",
    "wake_status": "Check wake word listener status and recent commands",
    "play_alarm": "Play built-in alarm sound (siren, beep, urgent, doorbell, etc.)",
    "play_file": "Play an audio file (WAV, MP3)",
    "stop_audio": "Stop any currently playing audio",
    "record": "Record audio from microphone",
    "list_devices": "List available audio input/output devices",
}

# Global state for audio playback
_audio_playing = False
_stop_requested = False
