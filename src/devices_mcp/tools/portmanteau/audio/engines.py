import asyncio
import contextlib
import io
import json as json_lib
import logging
import math
import os
import struct
import tempfile
import wave
from datetime import datetime
from typing import Any

import numpy as np

from .deps import (
    ALARM_SOUNDS,
    EDGE_TTS_AVAILABLE,
    FASTER_WHISPER_AVAILABLE,
    OPENWAKEWORD_AVAILABLE,
    PIPER_AVAILABLE,
    PYTTSX3_AVAILABLE,
    SOUNDDEVICE_AVAILABLE,
    STT_AVAILABLE,
    VOSK_AVAILABLE,
    WAKE_WORDS,
    WHISPER_AVAILABLE,
    OWWModel,
    WhisperModel,
    _detected_commands,
    _faster_whisper_model,
    _oww_model,
    _piper_voice,
    _vosk_model,
    _wake_command_queue,
    _wake_listener_running,
    _wake_listener_task,
    edge_tts,
    openwakeword,
    piper,
    pyttsx3,
    sd,
    sf,
    vosk,
    whisper,
)

logger = logging.getLogger(__name__)


def _generate_tone(frequency: float, duration: float, sample_rate: int = 44100) -> bytes:
    """Generate a sine wave tone as WAV bytes."""
    num_samples = int(sample_rate * duration)
    audio_data = []
    for i in range(num_samples):
        t = i / sample_rate
        envelope = min(1.0, i / 500) * min(1.0, (num_samples - i) / 500)
        sample = int(32767 * envelope * math.sin(2 * math.pi * frequency * t))
        audio_data.append(struct.pack("<h", sample))
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
                all_tones.append(b"\x00" * 4410)
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


async def _play_audio_bytes(audio_bytes: bytes) -> bool:
    """Play audio bytes through speakers."""
    global _stop_requested
    if not SOUNDDEVICE_AVAILABLE:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        try:
            if os.name == "nt":
                import winsound

                winsound.PlaySound(temp_path, winsound.SND_FILENAME)
            else:
                os.system(f"aplay {temp_path} 2>/dev/null || afplay {temp_path} 2>/dev/null")
            return True
        finally:
            os.unlink(temp_path)
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


async def _play_alarm_sound(alarm_type: str, repeat: int = 1) -> bool:
    """Generate and play an alarm sound."""
    audio_bytes = _generate_alarm_sound(alarm_type, repeat)
    return await _play_audio_bytes(audio_bytes)


# ============================================================================
# TTS ENGINES
# ============================================================================
async def _speak_with_piper(text: str, voice: str | None = None) -> dict[str, Any]:
    """TTS using Piper (best local quality)."""
    global _piper_voice
    if not PIPER_AVAILABLE:
        return {"success": False, "message": "Piper not available", "error": "Piper not available"}
    try:
        if _piper_voice is None:
            model_name = voice or "en_US-lessac-medium"
            _piper_voice = piper.PiperVoice.load(model_name)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        with wave.open(temp_path, "wb") as wav_file:
            _piper_voice.synthesize(text, wav_file)
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
        return {"success": False, "message": str(e), "error": str(e)}


async def _speak_with_edge(text: str, voice: str | None = None) -> dict[str, Any]:
    """TTS using Edge-TTS (Microsoft, needs internet)."""
    if not EDGE_TTS_AVAILABLE:
        return {"success": False, "message": "Edge-TTS not available", "error": "Edge-TTS not available"}
    try:
        voice = voice or "en-US-AriaNeural"
        communicate = edge_tts.Communicate(text, voice)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name
        await communicate.save(temp_path)
        if SOUNDDEVICE_AVAILABLE:
            data, samplerate = sf.read(temp_path)
            sd.play(data, samplerate)
            sd.wait()
        elif os.name == "nt":
            os.system(f'start /wait "" "{temp_path}"')
        else:
            os.system(f"mpg123 {temp_path} 2>/dev/null || afplay {temp_path}")
        os.unlink(temp_path)
        return {"success": True, "engine": "edge-tts", "voice": voice, "text": text}
    except Exception as e:
        logger.warning(f"Edge TTS failed: {e}")
        return {"success": False, "message": str(e), "error": str(e)}


async def _speak_with_pyttsx3(text: str, voice: str | None = None, rate: int = 150) -> dict[str, Any]:
    """TTS using pyttsx3 (offline, system voices)."""
    if not PYTTSX3_AVAILABLE:
        return {"success": False, "message": "pyttsx3 not available", "error": "pyttsx3 not available"}
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
        return {"success": False, "message": str(e), "error": str(e)}


async def _speak_text(text: str, voice: str | None = None, rate: int = 150, use_edge: bool = False) -> dict[str, Any]:
    """TTS with automatic fallback chain: Piper -> Edge-TTS -> pyttsx3."""
    errors = []
    if use_edge:
        result = await _speak_with_edge(text, voice)
        if result["success"]:
            return result
        errors.append(f"edge-tts: {result.get('error', 'failed')}")
    if PIPER_AVAILABLE:
        result = await _speak_with_piper(text, voice)
        if result["success"]:
            return result
        errors.append(f"piper: {result.get('error', 'failed')}")
    if EDGE_TTS_AVAILABLE and not use_edge:
        result = await _speak_with_edge(text, voice)
        if result["success"]:
            return result
        errors.append(f"edge-tts: {result.get('error', 'failed')}")
    if PYTTSX3_AVAILABLE:
        result = await _speak_with_pyttsx3(text, voice, rate)
        if result["success"]:
            return result
        errors.append(f"pyttsx3: {result.get('error', 'failed')}")
    return {
        "success": False,
        "message": f"All TTS engines failed: {'; '.join(errors)}",
        "error": f"All TTS engines failed: {'; '.join(errors)}",
        "install_hint": "pip install piper-tts edge-tts pyttsx3",
    }


# ============================================================================
# STT ENGINES
# ============================================================================
async def _transcribe_with_faster_whisper(audio_path: str, model: str = "base") -> dict[str, Any]:
    """STT using Faster-Whisper (SOTA, 4x faster than vanilla)."""
    global _faster_whisper_model
    if not FASTER_WHISPER_AVAILABLE:
        return {"success": False, "message": "Faster-Whisper not available", "error": "Faster-Whisper not available"}
    try:
        if _faster_whisper_model is None or getattr(_faster_whisper_model, "_model_size", None) != model:
            logger.info(f"Loading Faster-Whisper model: {model}")
            _faster_whisper_model = WhisperModel(model, device="cpu", compute_type="int8")
            _faster_whisper_model._model_size = model
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
        return {"success": False, "message": str(e), "error": str(e)}


async def _transcribe_with_vosk(audio_path: str) -> dict[str, Any]:
    """STT using Vosk (lightweight, fast)."""
    global _vosk_model
    if not VOSK_AVAILABLE:
        return {"success": False, "message": "Vosk not available", "error": "Vosk not available"}
    try:
        if _vosk_model is None:
            vosk.SetLogLevel(-1)
            model_path = vosk.Model(lang="en-us")
            _vosk_model = model_path
        data, samplerate = sf.read(audio_path, dtype="int16")
        rec = vosk.KaldiRecognizer(_vosk_model, samplerate)
        rec.AcceptWaveform(data.tobytes())
        result = json_lib.loads(rec.FinalResult())
        return {
            "success": True,
            "text": result.get("text", "").strip(),
            "engine": "vosk",
            "language": "en",
        }
    except Exception as e:
        logger.warning(f"Vosk failed: {e}")
        return {"success": False, "message": str(e), "error": str(e)}


async def _transcribe_with_whisper(audio_path: str, model: str = "base") -> dict[str, Any]:
    """STT using vanilla Whisper (fallback)."""
    if not WHISPER_AVAILABLE:
        return {"success": False, "message": "Whisper not available", "error": "Whisper not available"}
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
        return {"success": False, "message": str(e), "error": str(e)}


async def _transcribe_audio(audio_path: str, model: str = "base") -> dict[str, Any]:
    """STT with automatic fallback chain: Faster-Whisper -> Vosk -> Whisper."""
    errors = []
    if FASTER_WHISPER_AVAILABLE:
        result = await _transcribe_with_faster_whisper(audio_path, model)
        if result["success"]:
            return result
        errors.append(f"faster-whisper: {result.get('error', 'failed')}")
    if VOSK_AVAILABLE:
        result = await _transcribe_with_vosk(audio_path)
        if result["success"]:
            return result
        errors.append(f"vosk: {result.get('error', 'failed')}")
    if WHISPER_AVAILABLE:
        result = await _transcribe_with_whisper(audio_path, model)
        if result["success"]:
            return result
        errors.append(f"whisper: {result.get('error', 'failed')}")
    return {
        "success": False,
        "message": f"All STT engines failed: {'; '.join(errors)}",
        "error": f"All STT engines failed: {'; '.join(errors)}",
        "install_hint": "pip install faster-whisper vosk openai-whisper",
    }


# ============================================================================
# RECORDING
# ============================================================================
async def _record_audio(duration: float, sample_rate: int = 16000) -> tuple[str, bytes]:
    """Record audio from microphone."""
    if not SOUNDDEVICE_AVAILABLE:
        raise RuntimeError("Audio recording requires sounddevice. Install: pip install sounddevice soundfile")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()
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
            "message": "Voice commands require whisper and sounddevice. Install: pip install openai-whisper sounddevice soundfile",
            "error": "Voice commands require whisper and sounddevice. Install: pip install openai-whisper sounddevice soundfile",
        }
    try:
        temp_path, _ = await _record_audio(timeout)
        result = await _transcribe_audio(temp_path, model="base")
        os.unlink(temp_path)
        if not result["success"]:
            return result
        text = result["text"].lower()
        if wake_word:
            wake_found = any(w in text for w in [*WAKE_WORDS, wake_word.lower()])
            if not wake_found:
                return {
                    "success": True,
                    "wake_word_detected": False,
                    "text": result["text"],
                    "note": f"Wake word '{wake_word}' not detected",
                }
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
        return {"success": False, "message": f"Voice command failed: {e}", "error": f"Voice command failed: {e}"}


# ============================================================================
# ALWAYS-ON WAKE WORD LISTENER
# ============================================================================
async def _init_openwakeword() -> bool:
    """Initialize OpenWakeWord model (lazy load)."""
    global _oww_model
    if not OPENWAKEWORD_AVAILABLE:
        return False
    if _oww_model is not None:
        return True
    try:
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
    """Background loop that listens for wake word, then records and transcribes command."""
    global _wake_listener_running, _wake_command_queue
    if not SOUNDDEVICE_AVAILABLE:
        logger.error("Wake word listener requires sounddevice")
        return
    if _wake_command_queue is None:
        _wake_command_queue = asyncio.Queue()
    sample_rate = 16000
    chunk_size = 1280
    logger.info(f"Wake word listener started. Listening for '{wake_word}'...")
    try:
        if OPENWAKEWORD_AVAILABLE and _oww_model is not None:
            await _wake_listener_with_oww(wake_word, command_duration, threshold, sample_rate, chunk_size)
        else:
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
    stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16", blocksize=chunk_size)
    stream.start()
    try:
        while _wake_listener_running:
            audio_chunk, _ = stream.read(chunk_size)
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            predictions = _oww_model.predict(audio_np)
            for model_name, score in predictions.items():
                if score > threshold:
                    logger.info(f"Wake word detected! (model={model_name}, score={score:.2f})")
                    await _play_alarm_sound("attention", repeat=1)
                    logger.info(f"Recording command for {command_duration}s...")
                    temp_path, _ = await _record_audio(command_duration, sample_rate)
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
                        await _play_alarm_sound("success", repeat=1)
                    break
            await asyncio.sleep(0.01)
    finally:
        stream.stop()
        stream.close()


async def _wake_listener_with_vosk(wake_word: str, command_duration: float, sample_rate: int) -> None:
    """Wake word detection using Vosk streaming (fallback, still offline)."""
    if not VOSK_AVAILABLE:
        logger.error("Vosk not available for wake word fallback")
        return
    vosk.SetLogLevel(-1)
    model = vosk.Model(lang="en-us")
    rec = vosk.KaldiRecognizer(model, sample_rate)
    stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16", blocksize=4000)
    stream.start()
    try:
        while _wake_listener_running:
            audio_chunk, _ = stream.read(4000)
            if rec.AcceptWaveform(audio_chunk.tobytes()):
                vosk_result = json_lib.loads(rec.Result())
                text = vosk_result.get("text", "").lower()
                for ww in [wake_word.lower(), *[w.lower() for w in WAKE_WORDS]]:
                    if ww in text:
                        logger.info(f"Wake word '{ww}' detected in: {text}")
                        await _play_alarm_sound("attention", repeat=1)
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
            "message": "Wake word listener is already running",
            "error": "Wake word listener is already running",
            "status": "running",
        }
    if not SOUNDDEVICE_AVAILABLE:
        return {
            "success": False,
            "message": "Wake word listener requires sounddevice. Install: pip install sounddevice",
            "error": "Wake word listener requires sounddevice. Install: pip install sounddevice",
        }
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
            "message": "No wake word engine available. Install: pip install openwakeword vosk",
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
        return {"success": True, "status": "not_running", "note": "Wake word listener was not running"}
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
