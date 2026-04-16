"""
Audio Management Portmanteau Tool - "Alexa 2"

Comprehensive audio capabilities including TTS, STT, alarms, voice commands, and streaming.
Uses SOTA FOSS engines with automatic fallback chains:

STT Chain: Faster-Whisper -> Vosk -> Whisper (vanilla)
TTS Chain: Piper -> Edge-TTS -> pyttsx3
"""

import asyncio
import contextlib
import io
import logging
import os
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ============================================================================
# DEPENDENCY FLAGS - Ordered by preference (best first)
# ============================================================================

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

# ============================================================================
# STT ENGINE IMPORTS (order: faster-whisper > vosk > whisper)
# ============================================================================

# 1. Faster-Whisper (SOTA - 4x faster than vanilla Whisper)
try:
    from faster_whisper import WhisperModel

    FASTER_WHISPER_AVAILABLE = True
    logger.info("STT: faster-whisper available (primary)")
except ImportError:
    WhisperModel = None  # type: ignore[assignment, misc]

# 2. Vosk (lightweight, fast fallback)
try:
    import vosk

    VOSK_AVAILABLE = True
    logger.info("STT: vosk available (fallback)")
except ImportError:
    vosk = None  # type: ignore[assignment]

# 3. Vanilla Whisper (fallback)
try:
    import whisper

    WHISPER_AVAILABLE = True
    logger.info("STT: whisper available (fallback)")
except ImportError:
    whisper = None  # type: ignore[assignment]

STT_AVAILABLE = FASTER_WHISPER_AVAILABLE or VOSK_AVAILABLE or WHISPER_AVAILABLE

# ============================================================================
# TTS ENGINE IMPORTS (order: piper > edge-tts > pyttsx3)
# ============================================================================

# 1. Piper (SOTA local neural TTS)
try:
    import piper  # piper-tts package

    PIPER_AVAILABLE = True
    logger.info("TTS: piper available (primary)")
except ImportError:
    piper = None  # type: ignore[assignment]

# 2. Edge-TTS (Microsoft's free TTS, needs internet)
try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
    logger.info("TTS: edge-tts available (fallback)")
except ImportError:
    edge_tts = None  # type: ignore[assignment]

# 3. pyttsx3 (offline, uses system SAPI)
try:
    import pyttsx3

    PYTTSX3_AVAILABLE = True
    logger.info("TTS: pyttsx3 available (fallback)")
except ImportError:
    pyttsx3 = None  # type: ignore[assignment]

TTS_AVAILABLE = PIPER_AVAILABLE or EDGE_TTS_AVAILABLE or PYTTSX3_AVAILABLE

# ============================================================================
# AUDIO I/O
# ============================================================================

try:
    import sounddevice as sd
    import soundfile as sf

    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    sd = None  # type: ignore[assignment]
    sf = None  # type: ignore[assignment]

# ============================================================================
# WAKE WORD ENGINE (OpenWakeWord - fully offline, Alexa-style)
# ============================================================================

OPENWAKEWORD_AVAILABLE = False
try:
    import openwakeword
    from openwakeword.model import Model as OWWModel

    OPENWAKEWORD_AVAILABLE = True
    logger.info("Wake word: openwakeword available (always-on listening)")
except ImportError:
    openwakeword = None  # type: ignore[assignment]
    OWWModel = None  # type: ignore[assignment]

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

# Built-in alarm sounds (generated programmatically)
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

# Voice command keywords (two-word phrases reduce false positives from "taco" delivery guys)
WAKE_WORDS = ["hey tapo", "ok tapo", "yo tapo"]

AUDIO_ACTIONS = {
    "get_url": "Get RTSP stream URL with audio for a camera",
    "capabilities": "Get audio capabilities overview (TTS, STT, alarms, etc.)",
    "player_url": "Get URL for browser audio player page",
    "vlc_command": "Get VLC command to play camera stream with audio",
    # TTS actions
    "speak": "Text-to-speech: speak a message through speakers",
    "announce": "Announcement: speak message with attention chime first",
    # STT actions
    "listen": "Speech-to-text: listen and transcribe (requires microphone)",
    "voice_command": "Listen for voice command with wake word detection",
    # Always-on wake word (Alexa-style, fully offline)
    "wake_start": "Start always-on wake word listener (background, offline)",
    "wake_stop": "Stop the always-on wake word listener",
    "wake_status": "Check wake word listener status and recent commands",
    # Alarm/sound actions
    "play_alarm": "Play built-in alarm sound (siren, beep, urgent, doorbell, etc.)",
    "play_file": "Play an audio file (WAV, MP3)",
    "stop_audio": "Stop any currently playing audio",
    # Recording actions
    "record": "Record audio from microphone",
    "list_devices": "List available audio input/output devices",
}

# Global state for audio playback
_audio_playing = False
_stop_requested = False


def _generate_tone(frequency: float, duration: float, sample_rate: int = 44100) -> bytes:
    """Generate a sine wave tone as WAV bytes."""
    import math
    import struct

    num_samples = int(sample_rate * duration)
    audio_data = []

    for i in range(num_samples):
        t = i / sample_rate
        # Sine wave with fade in/out
        envelope = min(1.0, i / 500) * min(1.0, (num_samples - i) / 500)
        sample = int(32767 * envelope * math.sin(2 * math.pi * frequency * t))
        audio_data.append(struct.pack("<h", sample))

    # Create WAV in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(audio_data))

    return wav_buffer.getvalue()


def _generate_alarm_sound(alarm_type: str, repeat: int = 1) -> bytes:
    """Generate alarm sound based on type."""
    if alarm_type not in ALARM_SOUNDS:
        alarm_type = "beep"

    config = ALARM_SOUNDS[alarm_type]
    freqs = config["freq"]
    duration = config["duration"]
    pattern = config["pattern"]

    all_tones = []

    for _ in range(repeat):
        if pattern == "single":
            all_tones.append(_generate_tone(freqs[0], duration))
        elif pattern == "alternate":
            for freq in freqs * 3:
                all_tones.append(_generate_tone(freq, duration))
        elif pattern == "sequence":
            for freq in freqs:
                all_tones.append(_generate_tone(freq, duration))
        elif pattern == "ding_dong":
            all_tones.append(_generate_tone(freqs[0], duration))
            all_tones.append(_generate_tone(freqs[1], duration * 1.5))
        elif pattern == "cascade":
            for freq in freqs:
                all_tones.append(_generate_tone(freq, duration))
        elif pattern == "rapid":
            for _ in range(6):
                for freq in freqs:
                    all_tones.append(_generate_tone(freq, duration))
        elif pattern == "triple":
            for _ in range(3):
                all_tones.append(_generate_tone(freqs[0], duration))
                all_tones.append(b"\x00" * 4410)  # Short silence
        elif pattern == "ascending":
            for freq in freqs:
                all_tones.append(_generate_tone(freq, duration))
        elif pattern == "descending":
            for freq in reversed(freqs):
                all_tones.append(_generate_tone(freq, duration))
        elif pattern == "two_tone":
            for _ in range(2):
                for freq in freqs:
                    all_tones.append(_generate_tone(freq, duration))

    # Combine all tones into single WAV
    combined = io.BytesIO()
    with wave.open(combined, "wb") as wav_out:
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)
        wav_out.setframerate(44100)
        for tone_bytes in all_tones:
            tone_io = io.BytesIO(tone_bytes)
            with wave.open(tone_io, "rb") as wav_in:
                wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))

    return combined.getvalue()


async def _play_alarm_sound(alarm_type: str, repeat: int = 1) -> bool:
    """Generate and play an alarm sound."""
    audio_bytes = _generate_alarm_sound(alarm_type, repeat)
    return await _play_audio_bytes(audio_bytes)


async def _play_audio_bytes(audio_bytes: bytes) -> bool:
    """Play audio bytes through speakers."""
    global _audio_playing, _stop_requested

    if not SOUNDDEVICE_AVAILABLE:
        # Fallback: save to temp file and use system player
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            if os.name == "nt":
                import winsound

                winsound.PlaySound(temp_path, winsound.SND_FILENAME)
            else:
                # temp_path is controlled (from tempfile), safe to use
                os.system(f"aplay {temp_path} 2>/dev/null || afplay {temp_path} 2>/dev/null")  # noqa: S605
            return True
        finally:
            os.unlink(temp_path)

    # Use sounddevice
    _audio_playing = True
    _stop_requested = False

    try:
        audio_io = io.BytesIO(audio_bytes)
        data, samplerate = sf.read(audio_io)
        sd.play(data, samplerate)
        sd.wait()
        return True
    except Exception:
        logger.exception("Audio playback failed")
        return False
    finally:
        _audio_playing = False


async def _speak_with_piper(text: str, voice: str | None = None) -> dict[str, Any]:
    """TTS using Piper (best local quality)."""
    global _piper_voice

    if not PIPER_AVAILABLE:
        return {"success": False, "error": "Piper not available"}

    try:
        # Lazy load voice model
        if _piper_voice is None:
            # Default to en_US-lessac-medium (good quality, reasonable size)
            model_name = voice or "en_US-lessac-medium"
            _piper_voice = piper.PiperVoice.load(model_name)

        # Synthesize to WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        with wave.open(temp_path, "wb") as wav_file:
            _piper_voice.synthesize(text, wav_file)

        # Play audio
        if SOUNDDEVICE_AVAILABLE:
            data, samplerate = sf.read(temp_path)
            sd.play(data, samplerate)
            sd.wait()

        os.unlink(temp_path)
        return {
            "success": True,
            "engine": "piper",
            "voice": voice or "en_US-lessac-medium",
            "text": text,
        }
    except Exception as e:
        logger.warning(f"Piper TTS failed: {e}")
        return {"success": False, "error": str(e)}


async def _speak_with_edge(text: str, voice: str | None = None) -> dict[str, Any]:
    """TTS using Edge-TTS (Microsoft, needs internet)."""
    if not EDGE_TTS_AVAILABLE:
        return {"success": False, "error": "Edge-TTS not available"}

    try:
        voice = voice or "en-US-AriaNeural"
        communicate = edge_tts.Communicate(text, voice)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        await communicate.save(temp_path)

        # Play audio
        if SOUNDDEVICE_AVAILABLE:
            data, samplerate = sf.read(temp_path)
            sd.play(data, samplerate)
            sd.wait()
        elif os.name == "nt":
            os.system(f'start /wait "" "{temp_path}"')  # noqa: S605
        else:
            os.system(f"mpg123 {temp_path} 2>/dev/null || afplay {temp_path}")  # noqa: S605

        os.unlink(temp_path)
        return {"success": True, "engine": "edge-tts", "voice": voice, "text": text}
    except Exception as e:
        logger.warning(f"Edge TTS failed: {e}")
        return {"success": False, "error": str(e)}


async def _speak_with_pyttsx3(text: str, voice: str | None = None, rate: int = 150) -> dict[str, Any]:
    """TTS using pyttsx3 (offline, system voices)."""
    if not PYTTSX3_AVAILABLE:
        return {"success": False, "error": "pyttsx3 not available"}

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)

        if voice:
            voices = engine.getProperty("voices")
            for v in voices:
                if voice.lower() in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break

        engine.say(text)
        engine.runAndWait()
        return {"success": True, "engine": "pyttsx3", "text": text, "rate": rate}
    except Exception as e:
        logger.warning(f"pyttsx3 TTS failed: {e}")
        return {"success": False, "error": str(e)}


async def _speak_text(text: str, voice: str | None = None, rate: int = 150, use_edge: bool = False) -> dict[str, Any]:
    """
    TTS with automatic fallback chain: Piper -> Edge-TTS -> pyttsx3

    Args:
        text: Text to speak
        voice: Voice name/ID (engine-specific)
        rate: Speech rate for pyttsx3
        use_edge: Force Edge-TTS as primary (for high quality with internet)
    """
    errors = []

    # If user explicitly wants Edge-TTS, try it first
    if use_edge:
        result = await _speak_with_edge(text, voice)
        if result["success"]:
            return result
        errors.append(f"edge-tts: {result.get('error', 'failed')}")

    # 1. Try Piper (best local quality)
    if PIPER_AVAILABLE:
        result = await _speak_with_piper(text, voice)
        if result["success"]:
            return result
        errors.append(f"piper: {result.get('error', 'failed')}")

    # 2. Try Edge-TTS (needs internet)
    if EDGE_TTS_AVAILABLE and not use_edge:  # Skip if already tried
        result = await _speak_with_edge(text, voice)
        if result["success"]:
            return result
        errors.append(f"edge-tts: {result.get('error', 'failed')}")

    # 3. Fallback to pyttsx3 (offline, lower quality)
    if PYTTSX3_AVAILABLE:
        result = await _speak_with_pyttsx3(text, voice, rate)
        if result["success"]:
            return result
        errors.append(f"pyttsx3: {result.get('error', 'failed')}")

    # All engines failed
    return {
        "success": False,
        "error": f"All TTS engines failed: {'; '.join(errors)}",
        "install_hint": "pip install piper-tts edge-tts pyttsx3",
    }


async def _transcribe_with_faster_whisper(audio_path: str, model: str = "base") -> dict[str, Any]:
    """STT using Faster-Whisper (SOTA, 4x faster than vanilla)."""
    global _faster_whisper_model

    if not FASTER_WHISPER_AVAILABLE:
        return {"success": False, "error": "Faster-Whisper not available"}

    try:
        # Lazy load model
        if _faster_whisper_model is None or getattr(_faster_whisper_model, "_model_size", None) != model:
            logger.info(f"Loading Faster-Whisper model: {model}")
            _faster_whisper_model = WhisperModel(model, device="cpu", compute_type="int8")
            _faster_whisper_model._model_size = model  # type: ignore[attr-defined]

        segments, info = _faster_whisper_model.transcribe(audio_path, beam_size=5)
        text = " ".join(segment.text for segment in segments).strip()

        return {
            "success": True,
            "text": text,
            "language": info.language,
            "engine": "faster-whisper",
            "model": model,
        }
    except Exception as e:
        logger.warning(f"Faster-Whisper failed: {e}")
        return {"success": False, "error": str(e)}


async def _transcribe_with_vosk(audio_path: str) -> dict[str, Any]:
    """STT using Vosk (lightweight, fast)."""
    global _vosk_model

    if not VOSK_AVAILABLE:
        return {"success": False, "error": "Vosk not available"}

    try:
        import json

        # Lazy load model (auto-downloads on first use)
        if _vosk_model is None:
            # Use small English model by default
            vosk.SetLogLevel(-1)  # Suppress Vosk logs
            model_path = vosk.Model(lang="en-us")
            _vosk_model = model_path

        # Read audio file
        data, samplerate = sf.read(audio_path, dtype="int16")

        # Create recognizer
        rec = vosk.KaldiRecognizer(_vosk_model, samplerate)

        # Process audio
        rec.AcceptWaveform(data.tobytes())
        result = json.loads(rec.FinalResult())

        return {
            "success": True,
            "text": result.get("text", "").strip(),
            "engine": "vosk",
            "language": "en",
        }
    except Exception as e:
        logger.warning(f"Vosk failed: {e}")
        return {"success": False, "error": str(e)}


async def _transcribe_with_whisper(audio_path: str, model: str = "base") -> dict[str, Any]:
    """STT using vanilla Whisper (fallback)."""
    if not WHISPER_AVAILABLE:
        return {"success": False, "error": "Whisper not available"}

    try:
        whisper_model = whisper.load_model(model)
        result = whisper_model.transcribe(audio_path)
        return {
            "success": True,
            "text": result["text"].strip(),
            "language": result.get("language", "unknown"),
            "engine": "whisper",
            "model": model,
        }
    except Exception as e:
        logger.warning(f"Whisper failed: {e}")
        return {"success": False, "error": str(e)}


async def _transcribe_audio(audio_path: str, model: str = "base") -> dict[str, Any]:
    """
    STT with automatic fallback chain: Faster-Whisper -> Vosk -> Whisper

    Args:
        audio_path: Path to audio file
        model: Model size for Whisper engines (tiny, base, small, medium, large)
    """
    errors = []

    # 1. Try Faster-Whisper (SOTA, fastest high-quality)
    if FASTER_WHISPER_AVAILABLE:
        result = await _transcribe_with_faster_whisper(audio_path, model)
        if result["success"]:
            return result
        errors.append(f"faster-whisper: {result.get('error', 'failed')}")

    # 2. Try Vosk (lightweight, fast)
    if VOSK_AVAILABLE:
        result = await _transcribe_with_vosk(audio_path)
        if result["success"]:
            return result
        errors.append(f"vosk: {result.get('error', 'failed')}")

    # 3. Fallback to vanilla Whisper
    if WHISPER_AVAILABLE:
        result = await _transcribe_with_whisper(audio_path, model)
        if result["success"]:
            return result
        errors.append(f"whisper: {result.get('error', 'failed')}")

    # All engines failed
    return {
        "success": False,
        "error": f"All STT engines failed: {'; '.join(errors)}",
        "install_hint": "pip install faster-whisper vosk openai-whisper",
    }


async def _record_audio(duration: float, sample_rate: int = 16000) -> tuple[str, bytes]:
    """Record audio from microphone."""
    if not SOUNDDEVICE_AVAILABLE:
        raise RuntimeError("Audio recording requires sounddevice. Install: pip install sounddevice soundfile")

    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()

    # Save to temp file (using NamedTemporaryFile for security)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
    sf.write(temp_path, recording, sample_rate)

    with open(temp_path, "rb") as f:
        audio_bytes = f.read()

    return temp_path, audio_bytes


async def _listen_for_command(timeout: float = 5.0, wake_word: str | None = None) -> dict[str, Any]:
    """Listen for voice command, optionally with wake word detection."""
    if not STT_AVAILABLE or not SOUNDDEVICE_AVAILABLE:
        return {
            "success": False,
            "error": "Voice commands require whisper and sounddevice. Install: pip install openai-whisper sounddevice soundfile",
        }

    try:
        # Record audio
        temp_path, _ = await _record_audio(timeout)

        # Transcribe
        result = await _transcribe_audio(temp_path, model="base")
        os.unlink(temp_path)

        if not result["success"]:
            return result

        text = result["text"].lower()

        # Check for wake word if specified
        if wake_word:
            wake_found = any(w in text for w in [*WAKE_WORDS, wake_word.lower()])
            if not wake_found:
                return {
                    "success": True,
                    "wake_word_detected": False,
                    "text": result["text"],
                    "note": f"Wake word '{wake_word}' not detected",
                }

            # Extract command after wake word
            command = result["text"]
            for w in [*WAKE_WORDS, wake_word.lower()]:
                if w in text:
                    idx = text.find(w)
                    command = result["text"][idx + len(w) :].strip()
                    break

            return {
                "success": True,
                "wake_word_detected": True,
                "wake_word": wake_word,
                "command": command,
                "full_text": result["text"],
            }

        return {
            "success": True,
            "text": result["text"],
            "language": result.get("language"),
        }
    except Exception as e:
        return {"success": False, "error": f"Voice command failed: {e}"}


# ============================================================================
# ALWAYS-ON WAKE WORD LISTENER (Alexa-style, fully offline)
# ============================================================================


async def _init_openwakeword() -> bool:
    """Initialize OpenWakeWord model (lazy load)."""
    global _oww_model

    if not OPENWAKEWORD_AVAILABLE:
        return False

    if _oww_model is not None:
        return True

    try:
        # Download and load default models (includes "hey jarvis", "alexa", etc.)
        # We'll use the generic model and do text matching for "hey tapo"
        openwakeword.utils.download_models()
        _oww_model = OWWModel(inference_framework="onnx")
        logger.info("OpenWakeWord model initialized")
        return True
    except Exception:
        logger.exception("Failed to initialize OpenWakeWord")
        return False


async def _wake_word_listener_loop(
    wake_word: str = "hey tapo",
    command_duration: float = 5.0,
    threshold: float = 0.5,
) -> None:
    """
    Background loop that listens for wake word, then records and transcribes command.
    Fully offline - no network traffic.
    """
    global _wake_listener_running, _wake_command_queue

    if not SOUNDDEVICE_AVAILABLE:
        logger.error("Wake word listener requires sounddevice")
        return

    # Initialize queue for detected commands
    if _wake_command_queue is None:
        _wake_command_queue = asyncio.Queue()

    sample_rate = 16000
    chunk_size = 1280  # ~80ms chunks for OpenWakeWord

    logger.info(f"Wake word listener started. Listening for '{wake_word}'...")

    try:
        # If OpenWakeWord available, use it for efficient wake word detection
        if OPENWAKEWORD_AVAILABLE and _oww_model is not None:
            await _wake_listener_with_oww(wake_word, command_duration, threshold, sample_rate, chunk_size)
        else:
            # Fallback: Use Vosk keyword spotting or periodic STT
            await _wake_listener_with_vosk(wake_word, command_duration, sample_rate)

    except asyncio.CancelledError:
        logger.info("Wake word listener cancelled")
    except Exception:
        logger.exception("Wake word listener error")
    finally:
        _wake_listener_running = False
        logger.info("Wake word listener stopped")


async def _wake_listener_with_oww(
    wake_word: str,
    command_duration: float,
    threshold: float,
    sample_rate: int,
    chunk_size: int,
) -> None:
    """Wake word detection using OpenWakeWord (most efficient)."""
    import numpy as np

    # Create audio stream
    stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16", blocksize=chunk_size)
    stream.start()

    try:
        while _wake_listener_running:
            # Read audio chunk
            audio_chunk, _ = stream.read(chunk_size)
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0

            # Run wake word detection
            predictions = _oww_model.predict(audio_np)

            # Check for any wake word activation
            # OpenWakeWord uses generic models - we check if any model activates
            for model_name, score in predictions.items():
                if score > threshold:
                    logger.info(f"Wake word detected! (model={model_name}, score={score:.2f})")

                    # Play acknowledgment beep
                    await _play_alarm_sound("attention", repeat=1)

                    # Record command
                    logger.info(f"Recording command for {command_duration}s...")
                    temp_path, _ = await _record_audio(command_duration, sample_rate)

                    # Transcribe
                    result = await _transcribe_audio(temp_path)
                    os.unlink(temp_path)

                    if result["success"]:
                        command_text = result["text"]
                        detection = {
                            "timestamp": datetime.now().isoformat(),
                            "wake_model": model_name,
                            "confidence": score,
                            "command": command_text,
                            "engine": result.get("engine", "unknown"),
                        }
                        _detected_commands.append(detection)
                        if _wake_command_queue:
                            await _wake_command_queue.put(detection)
                        logger.info(f"Command detected: {command_text}")

                        # Play success chime
                        await _play_alarm_sound("success", repeat=1)
                    break

            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.01)

    finally:
        stream.stop()
        stream.close()


async def _wake_listener_with_vosk(
    wake_word: str,
    command_duration: float,
    sample_rate: int,
) -> None:
    """Wake word detection using Vosk streaming (fallback, still offline)."""
    if not VOSK_AVAILABLE:
        logger.error("Vosk not available for wake word fallback")
        return

    import json

    # Initialize Vosk model
    vosk.SetLogLevel(-1)
    model = vosk.Model(lang="en-us")
    rec = vosk.KaldiRecognizer(model, sample_rate)

    # Create audio stream
    stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16", blocksize=4000)
    stream.start()

    try:
        while _wake_listener_running:
            audio_chunk, _ = stream.read(4000)

            if rec.AcceptWaveform(audio_chunk.tobytes()):
                vosk_result = json.loads(rec.Result())
                text = vosk_result.get("text", "").lower()

                # Check for wake word in recognized text
                for ww in [wake_word.lower(), *[w.lower() for w in WAKE_WORDS]]:
                    if ww in text:
                        logger.info(f"Wake word '{ww}' detected in: {text}")

                        # Play acknowledgment
                        await _play_alarm_sound("attention", repeat=1)

                        # Record command
                        temp_path, _ = await _record_audio(command_duration, sample_rate)
                        transcribe_result = await _transcribe_audio(temp_path)
                        os.unlink(temp_path)

                        if transcribe_result["success"]:
                            detection = {
                                "timestamp": datetime.now().isoformat(),
                                "wake_word": ww,
                                "command": transcribe_result["text"],
                                "engine": transcribe_result.get("engine", "vosk-trigger"),
                            }
                            _detected_commands.append(detection)
                            if _wake_command_queue:
                                await _wake_command_queue.put(detection)
                            logger.info(f"Command: {transcribe_result['text']}")
                            await _play_alarm_sound("success", repeat=1)
                        break

            await asyncio.sleep(0.01)

    finally:
        stream.stop()
        stream.close()


async def _start_wake_listener(wake_word: str = "hey tapo", command_duration: float = 5.0) -> dict[str, Any]:
    """Start the always-on wake word listener in background."""
    global _wake_listener_running, _wake_listener_task

    if _wake_listener_running:
        return {
            "success": False,
            "error": "Wake word listener is already running",
            "status": "running",
        }

    if not SOUNDDEVICE_AVAILABLE:
        return {
            "success": False,
            "error": "Wake word listener requires sounddevice. Install: pip install sounddevice",
        }

    # Check for wake word engine
    engine = "none"
    if OPENWAKEWORD_AVAILABLE:
        if not await _init_openwakeword():
            logger.warning("OpenWakeWord init failed, will use Vosk fallback")
        else:
            engine = "openwakeword"

    if engine == "none" and VOSK_AVAILABLE:
        engine = "vosk"
    elif engine == "none":
        return {
            "success": False,
            "error": "No wake word engine available. Install: pip install openwakeword vosk",
        }

    _wake_listener_running = True
    _wake_listener_task = asyncio.create_task(_wake_word_listener_loop(wake_word, command_duration))

    return {
        "success": True,
        "status": "started",
        "wake_word": wake_word,
        "command_duration": command_duration,
        "engine": engine,
        "note": "Listener running in background. Say wake word to activate.",
    }


async def _stop_wake_listener() -> dict[str, Any]:
    """Stop the always-on wake word listener."""
    global _wake_listener_running, _wake_listener_task

    if not _wake_listener_running:
        return {
            "success": True,
            "status": "not_running",
            "note": "Wake word listener was not running",
        }

    _wake_listener_running = False

    if _wake_listener_task:
        _wake_listener_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _wake_listener_task
        _wake_listener_task = None

    return {
        "success": True,
        "status": "stopped",
        "recent_commands": _detected_commands[-5:] if _detected_commands else [],
    }


def _get_wake_status() -> dict[str, Any]:
    """Get wake word listener status."""
    engine = "none"
    if OPENWAKEWORD_AVAILABLE:
        engine = "openwakeword"
    elif VOSK_AVAILABLE:
        engine = "vosk"

    return {
        "running": _wake_listener_running,
        "engine": engine,
        "openwakeword_available": OPENWAKEWORD_AVAILABLE,
        "vosk_available": VOSK_AVAILABLE,
        "sounddevice_available": SOUNDDEVICE_AVAILABLE,
        "recent_commands": _detected_commands[-10:] if _detected_commands else [],
        "total_detections": len(_detected_commands),
        "wake_words": WAKE_WORDS,
    }


def register_audio_management_tool(mcp: FastMCP) -> None:
    """Register the audio management portmanteau tool."""

    @mcp.tool()
    async def audio_management(
        action: Literal[
            "get_url",
            "capabilities",
            "player_url",
            "vlc_command",
            "speak",
            "announce",
            "listen",
            "voice_command",
            "wake_start",
            "wake_stop",
            "wake_status",
            "play_alarm",
            "play_file",
            "stop_audio",
            "record",
            "list_devices",
        ],
        camera_id: str | None = None,
        # TTS parameters
        text: str | None = None,
        voice: str | None = None,
        rate: int = 150,
        use_edge_tts: bool = False,
        # Alarm parameters
        alarm_type: Literal[
            "siren",
            "beep",
            "urgent",
            "doorbell",
            "chime",
            "alarm",
            "attention",
            "success",
            "error",
            "alert",
        ] = "beep",
        repeat: int = 1,
        # Audio file parameters
        file_path: str | None = None,
        # Recording/listening parameters
        duration: float = 5.0,
        wake_word: str | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive audio management portmanteau tool - "Alexa 2".

        PORTMANTEAU PATTERN RATIONALE:
        Consolidates ALL audio operations into a single interface: streaming, TTS, STT,
        alarms, voice commands, and recording. Transforms the system into a voice-capable
        smart home assistant.

        Args:
            action (Literal, required): The operation to perform. Must be one of:
                STREAMING:
                - "get_url": Get RTSP stream URL with audio (requires: camera_id)
                - "capabilities": Get full audio capabilities overview
                - "player_url": Get browser player page URL (requires: camera_id)
                - "vlc_command": Get VLC command to play stream (requires: camera_id)

                TEXT-TO-SPEECH:
                - "speak": Speak text through speakers (requires: text)
                - "announce": Play attention chime then speak (requires: text)

                SPEECH-TO-TEXT:
                - "listen": Record and transcribe speech (optional: duration)
                - "voice_command": Listen for wake word + command (optional: wake_word, duration)

                ALARMS & SOUNDS:
                - "play_alarm": Play built-in alarm (optional: alarm_type, repeat)
                - "play_file": Play audio file (requires: file_path)
                - "stop_audio": Stop any currently playing audio

                RECORDING:
                - "record": Record audio from microphone (optional: duration)
                - "list_devices": List available audio input/output devices

            camera_id (str | None): Camera ID for streaming actions.
            text (str | None): Text to speak for TTS actions.
            voice (str | None): Voice name/ID for TTS (system-dependent).
            rate (int): Speech rate for pyttsx3 (default: 150 words/min).
            use_edge_tts (bool): Use Microsoft Edge TTS for better quality (requires internet).
            alarm_type: Built-in alarm type (siren, beep, urgent, doorbell, chime, alarm, attention, success, error, alert).
            repeat (int): Number of times to repeat alarm (default: 1).
            file_path (str | None): Path to audio file for play_file action.
            duration (float): Recording/listening duration in seconds (default: 5.0).
            wake_word (str | None): Custom wake word for voice_command action.

        Returns:
            dict[str, Any]: Operation-specific result

        Examples:
            # TTS - speak a message
            audio_management(action="speak", text="Intruder detected in backyard!")

            # Announcement with chime
            audio_management(action="announce", text="Package delivered at front door")

            # Play alarm
            audio_management(action="play_alarm", alarm_type="siren", repeat=3)

            # Listen for voice command
            audio_management(action="voice_command", wake_word="hey tapo", duration=10)

            # Record audio
            audio_management(action="record", duration=30)

            # List audio devices
            audio_management(action="list_devices")
        """
        try:
            if action not in AUDIO_ACTIONS:
                return {
                    "success": False,
                    "error": f"Invalid action '{action}'. Available: {list(AUDIO_ACTIONS.keys())}",
                    "available_actions": AUDIO_ACTIONS,
                }

            logger.info(f"Executing audio management action: {action}")

            # ===== CAPABILITIES =====
            if action == "capabilities":
                # Determine active engines
                stt_primary = (
                    "faster-whisper"
                    if FASTER_WHISPER_AVAILABLE
                    else "vosk"
                    if VOSK_AVAILABLE
                    else "whisper"
                    if WHISPER_AVAILABLE
                    else None
                )
                tts_primary = (
                    "piper"
                    if PIPER_AVAILABLE
                    else "edge-tts"
                    if EDGE_TTS_AVAILABLE
                    else "pyttsx3"
                    if PYTTSX3_AVAILABLE
                    else None
                )

                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "stt_engines": {
                            "primary": stt_primary,
                            "fallback_chain": "faster-whisper -> vosk -> whisper",
                            "faster_whisper": {
                                "available": FASTER_WHISPER_AVAILABLE,
                                "quality": "⭐⭐⭐⭐⭐",
                                "speed": "4x faster than vanilla",
                                "note": "SOTA - CTranslate2 optimized",
                            },
                            "vosk": {
                                "available": VOSK_AVAILABLE,
                                "quality": "⭐⭐⭐⭐",
                                "speed": "Fast",
                                "note": "Lightweight, great for real-time",
                            },
                            "whisper": {
                                "available": WHISPER_AVAILABLE,
                                "quality": "⭐⭐⭐⭐⭐",
                                "speed": "Slow",
                                "note": "Original OpenAI Whisper",
                            },
                        },
                        "tts_engines": {
                            "primary": tts_primary,
                            "fallback_chain": "piper -> edge-tts -> pyttsx3",
                            "piper": {
                                "available": PIPER_AVAILABLE,
                                "quality": "⭐⭐⭐⭐⭐",
                                "offline": True,
                                "note": "SOTA local neural TTS",
                            },
                            "edge_tts": {
                                "available": EDGE_TTS_AVAILABLE,
                                "quality": "⭐⭐⭐⭐⭐",
                                "offline": False,
                                "note": "Microsoft neural voices (needs internet)",
                            },
                            "pyttsx3": {
                                "available": PYTTSX3_AVAILABLE,
                                "quality": "⭐⭐",
                                "offline": True,
                                "note": "System SAPI voices",
                            },
                        },
                        "audio_io": {
                            "sounddevice": SOUNDDEVICE_AVAILABLE,
                            "note": "Required for playback and recording",
                        },
                        "wake_word_detection": {
                            "primary": "openwakeword" if OPENWAKEWORD_AVAILABLE else "vosk" if VOSK_AVAILABLE else None,
                            "openwakeword": {
                                "available": OPENWAKEWORD_AVAILABLE,
                                "quality": "⭐⭐⭐⭐⭐",
                                "offline": True,
                                "always_on": True,
                                "note": "Alexa-style always-on detection",
                            },
                            "vosk_fallback": {
                                "available": VOSK_AVAILABLE,
                                "quality": "⭐⭐⭐",
                                "offline": True,
                                "always_on": True,
                                "note": "Streaming keyword spotting fallback",
                            },
                            "listener_running": _wake_listener_running,
                        },
                        "alarm_types": list(ALARM_SOUNDS.keys()),
                        "wake_words": WAKE_WORDS,
                        "camera_audio": {
                            "onvif_cameras": {"listen": True, "speak": False},
                            "ring_doorbell": {"listen": True, "speak": True},
                        },
                        "install_commands": {
                            "wake_word": "pip install openwakeword",
                            "stt_sota": "pip install faster-whisper",
                            "stt_fallback": "pip install vosk",
                            "tts_sota": "pip install piper-tts",
                            "tts_fallback": "pip install edge-tts pyttsx3",
                            "audio_io": "pip install sounddevice soundfile",
                            "all": "pip install openwakeword faster-whisper vosk piper-tts edge-tts pyttsx3 sounddevice soundfile",
                        },
                    },
                }

            # ===== TEXT-TO-SPEECH =====
            if action == "speak":
                if not text:
                    return {
                        "success": False,
                        "action": action,
                        "error": "text is required for speak action",
                    }
                result = await _speak_text(text, voice=voice, rate=rate, use_edge=use_edge_tts)
                return {"success": result["success"], "action": action, "data": result}

            if action == "announce":
                if not text:
                    return {
                        "success": False,
                        "action": action,
                        "error": "text is required for announce action",
                    }
                # Play attention chime first
                chime_sound = _generate_alarm_sound("chime", repeat=1)
                await _play_audio_bytes(chime_sound)
                await asyncio.sleep(0.3)
                # Then speak
                result = await _speak_text(text, voice=voice, rate=rate, use_edge=use_edge_tts)
                return {"success": result["success"], "action": action, "data": result}

            # ===== SPEECH-TO-TEXT =====
            if action == "listen":
                if not STT_AVAILABLE or not SOUNDDEVICE_AVAILABLE:
                    return {
                        "success": False,
                        "action": action,
                        "error": "Listen requires whisper and sounddevice. Install: pip install openai-whisper sounddevice soundfile",
                    }
                temp_path, _ = await _record_audio(duration)
                result = await _transcribe_audio(temp_path)
                os.unlink(temp_path)
                return {"success": result["success"], "action": action, "data": result}

            if action == "voice_command":
                result = await _listen_for_command(timeout=duration, wake_word=wake_word or "tapo")
                return {"success": result["success"], "action": action, "data": result}

            # ===== ALWAYS-ON WAKE WORD (Alexa-style) =====
            if action == "wake_start":
                result = await _start_wake_listener(
                    wake_word=wake_word or "hey tapo",
                    command_duration=duration,
                )
                return {"success": result["success"], "action": action, "data": result}

            if action == "wake_stop":
                result = await _stop_wake_listener()
                return {"success": result["success"], "action": action, "data": result}

            if action == "wake_status":
                status = _get_wake_status()
                return {"success": True, "action": action, "data": status}

            # ===== ALARMS & SOUNDS =====
            if action == "play_alarm":
                alarm_sound = _generate_alarm_sound(alarm_type, repeat=repeat)
                success = await _play_audio_bytes(alarm_sound)
                return {
                    "success": success,
                    "action": action,
                    "data": {"alarm_type": alarm_type, "repeat": repeat},
                }

            if action == "play_file":
                if not file_path:
                    return {
                        "success": False,
                        "action": action,
                        "error": "file_path is required for play_file action",
                    }
                if not Path(file_path).exists():
                    return {
                        "success": False,
                        "action": action,
                        "error": f"File not found: {file_path}",
                    }
                with open(file_path, "rb") as f:
                    audio_bytes = f.read()
                success = await _play_audio_bytes(audio_bytes)
                return {"success": success, "action": action, "data": {"file": file_path}}

            if action == "stop_audio":
                global _stop_requested
                _stop_requested = True
                if SOUNDDEVICE_AVAILABLE:
                    sd.stop()
                return {"success": True, "action": action, "data": {"message": "Audio stopped"}}

            # ===== RECORDING =====
            if action == "record":
                if not SOUNDDEVICE_AVAILABLE:
                    return {
                        "success": False,
                        "action": action,
                        "error": "Recording requires sounddevice. Install: pip install sounddevice soundfile",
                    }
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = Path(tempfile.gettempdir()) / f"recording_{timestamp}.wav"
                temp_path, audio_bytes = await _record_audio(duration)
                # Move to output path
                Path(temp_path).rename(output_path)
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "file": str(output_path),
                        "duration": duration,
                        "size_bytes": len(audio_bytes),
                    },
                }

            if action == "list_devices":
                devices_info = {"input": [], "output": []}
                if SOUNDDEVICE_AVAILABLE:
                    devices = sd.query_devices()
                    for i, dev in enumerate(devices):
                        dev_info = {
                            "id": i,
                            "name": dev["name"],
                            "channels": dev["max_input_channels"],
                        }
                        if dev["max_input_channels"] > 0:
                            devices_info["input"].append(dev_info)
                        if dev["max_output_channels"] > 0:
                            dev_info["channels"] = dev["max_output_channels"]
                            devices_info["output"].append(dev_info)
                else:
                    devices_info["error"] = "sounddevice not available"
                return {"success": True, "action": action, "data": devices_info}

            # ===== CAMERA STREAMING (original actions) =====

            # Other actions require camera_id
            if not camera_id:
                return {
                    "success": False,
                    "action": action,
                    "error": f"camera_id is required for '{action}' action",
                }

            # Get camera and RTSP URL
            from urllib.parse import urlparse

            from devices_mcp.core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            camera = await server.camera_manager.get_camera(camera_id)

            if not camera:
                return {
                    "success": False,
                    "action": action,
                    "error": f"Camera '{camera_id}' not found",
                }

            # Connect if needed
            if not await camera.is_connected():
                await camera.connect()

            # Get stream URL
            stream_url = await camera.get_stream_url()
            if not stream_url:
                return {
                    "success": False,
                    "action": action,
                    "error": f"Could not get stream URL for '{camera_id}'",
                }

            # Add auth credentials
            parsed = urlparse(stream_url)
            username = camera.config.params.get("username", "")
            password = camera.config.params.get("password", "")

            if username and password:
                auth_url = f"rtsp://{username}:{password}@{parsed.hostname}:{parsed.port or 554}{parsed.path}"
            else:
                auth_url = stream_url

            # Safe URL (no password) for display
            safe_url = f"rtsp://{parsed.hostname}:{parsed.port or 554}{parsed.path}"

            if action == "get_url":
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "camera_id": camera_id,
                        "rtsp_url": auth_url,
                        "rtsp_url_safe": safe_url,
                        "audio_capable": True,
                        "two_way_audio": False,
                        "note": "Open this URL in VLC for video + audio playback",
                    },
                }

            if action == "player_url":
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "camera_id": camera_id,
                        "player_url": f"/api/audio/player/{camera_id}",
                        "vlc_link_url": f"/api/audio/vlc-link/{camera_id}",
                        "note": "Open player_url in browser for audio controls",
                    },
                }

            if action == "vlc_command":
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "camera_id": camera_id,
                        "vlc_command": f'vlc "{auth_url}"',
                        "ffplay_command": f'ffplay -i "{auth_url}"',
                        "note": "Run these commands in terminal to play stream with audio",
                    },
                }

            return {"success": False, "error": f"Action '{action}' not implemented"}

        except Exception as e:
            logger.exception(f"Error in audio management action '{action}'")
            return {"success": False, "action": action, "error": str(e)}
