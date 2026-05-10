import asyncio
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP

from .deps import (
    ALARM_SOUNDS,
    AUDIO_ACTIONS,
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
    _wake_listener_running,
    sd,
)
from .engines import (
    _generate_alarm_sound,
    _get_wake_status,
    _listen_for_command,
    _play_audio_bytes,
    _record_audio,
    _speak_text,
    _start_wake_listener,
    _stop_wake_listener,
    _transcribe_audio,
)

logger = logging.getLogger(__name__)


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
        text: str | None = None,
        voice: str | None = None,
        rate: int = 150,
        use_edge_tts: bool = False,
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
        file_path: str | None = None,
        duration: float = 5.0,
        wake_word: str | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive audio management portmanteau tool - "Alexa 2".

        Consolidates ALL audio operations into a single interface: streaming, TTS, STT,
        alarms, voice commands, and recording.

        Args:
            action: The operation to perform.
                STREAMING: "get_url", "capabilities", "player_url", "vlc_command"
                TEXT-TO-SPEECH: "speak", "announce" (requires: text)
                SPEECH-TO-TEXT: "listen", "voice_command" (optional: wake_word, duration)
                ALARMS: "play_alarm", "play_file" (requires: file_path), "stop_audio"
                RECORDING: "record", "list_devices"
            camera_id: Camera ID for streaming actions.
            text: Text to speak for TTS actions.
            voice: Voice name/ID for TTS.
            rate: Speech rate for pyttsx3 (default: 150).
            use_edge_tts: Use Microsoft Edge TTS for better quality (requires internet).
            alarm_type: Built-in alarm type.
            repeat: Number of times to repeat alarm (default: 1).
            file_path: Path to audio file for play_file action.
            duration: Recording/listening duration in seconds (default: 5.0).
            wake_word: Custom wake word for voice_command action.

        Returns:
            Operation-specific result dict.
        """
        try:
            if action not in AUDIO_ACTIONS:
                return {
                    "success": False,
                    "error": f"Invalid action '{action}'. Available: {list(AUDIO_ACTIONS.keys())}",
                    "available_actions": AUDIO_ACTIONS,
                }

            logger.info(f"Executing audio management action: {action}")

            if action == "capabilities":
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
                                "quality": "5/5",
                                "speed": "4x faster than vanilla",
                                "note": "CTranslate2 optimized",
                            },
                            "vosk": {
                                "available": VOSK_AVAILABLE,
                                "quality": "4/5",
                                "speed": "Fast",
                                "note": "Lightweight, great for real-time",
                            },
                            "whisper": {
                                "available": WHISPER_AVAILABLE,
                                "quality": "5/5",
                                "speed": "Slow",
                                "note": "Original OpenAI Whisper",
                            },
                        },
                        "tts_engines": {
                            "primary": tts_primary,
                            "fallback_chain": "piper -> edge-tts -> pyttsx3",
                            "piper": {
                                "available": PIPER_AVAILABLE,
                                "quality": "5/5",
                                "offline": True,
                                "note": "SOTA local neural TTS",
                            },
                            "edge_tts": {
                                "available": EDGE_TTS_AVAILABLE,
                                "quality": "5/5",
                                "offline": False,
                                "note": "Microsoft neural voices (needs internet)",
                            },
                            "pyttsx3": {
                                "available": PYTTSX3_AVAILABLE,
                                "quality": "2/5",
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
                                "quality": "5/5",
                                "offline": True,
                                "always_on": True,
                                "note": "Alexa-style always-on detection",
                            },
                            "vosk_fallback": {
                                "available": VOSK_AVAILABLE,
                                "quality": "3/5",
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

            if action == "speak":
                if not text:
                    return {"success": False, "action": action, "error": "text is required for speak action"}
                result = await _speak_text(text, voice=voice, rate=rate, use_edge=use_edge_tts)
                return {"success": result["success"], "action": action, "data": result}

            if action == "announce":
                if not text:
                    return {"success": False, "action": action, "error": "text is required for announce action"}
                chime_sound = _generate_alarm_sound("chime", repeat=1)
                await _play_audio_bytes(chime_sound)
                await asyncio.sleep(0.3)
                result = await _speak_text(text, voice=voice, rate=rate, use_edge=use_edge_tts)
                return {"success": result["success"], "action": action, "data": result}

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

            if action == "wake_start":
                result = await _start_wake_listener(wake_word=wake_word or "hey tapo", command_duration=duration)
                return {"success": result["success"], "action": action, "data": result}

            if action == "wake_stop":
                result = await _stop_wake_listener()
                return {"success": result["success"], "action": action, "data": result}

            if action == "wake_status":
                status = _get_wake_status()
                return {"success": True, "action": action, "data": status}

            if action == "play_alarm":
                alarm_sound = _generate_alarm_sound(alarm_type, repeat=repeat)
                success = await _play_audio_bytes(alarm_sound)
                return {"success": success, "action": action, "data": {"alarm_type": alarm_type, "repeat": repeat}}

            if action == "play_file":
                if not file_path:
                    return {"success": False, "action": action, "error": "file_path is required for play_file action"}
                if not Path(file_path).exists():
                    return {"success": False, "action": action, "error": f"File not found: {file_path}"}
                with open(file_path, "rb") as f:
                    audio_bytes = f.read()
                success = await _play_audio_bytes(audio_bytes)
                return {"success": success, "action": action, "data": {"file": file_path}}

            if action == "stop_audio":
                if SOUNDDEVICE_AVAILABLE:
                    sd.stop()
                return {"success": True, "action": action, "data": {"message": "Audio stopped"}}

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
                Path(temp_path).rename(output_path)
                return {
                    "success": True,
                    "action": action,
                    "data": {"file": str(output_path), "duration": duration, "size_bytes": len(audio_bytes)},
                }

            if action == "list_devices":
                devices_info = {"input": [], "output": []}
                if SOUNDDEVICE_AVAILABLE:
                    devices = sd.query_devices()
                    for i, dev in enumerate(devices):
                        dev_info = {"id": i, "name": dev["name"], "channels": dev["max_input_channels"]}
                        if dev["max_input_channels"] > 0:
                            devices_info["input"].append(dev_info)
                        if dev["max_output_channels"] > 0:
                            dev_info["channels"] = dev["max_output_channels"]
                            devices_info["output"].append(dev_info)
                else:
                    devices_info["error"] = "sounddevice not available"
                return {"success": True, "action": action, "data": devices_info}

            if not camera_id:
                return {"success": False, "action": action, "error": f"camera_id is required for '{action}' action"}

            from urllib.parse import urlparse

            from devices_mcp.core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            camera = await server.camera_manager.get_camera(camera_id)

            if not camera:
                return {"success": False, "action": action, "error": f"Camera '{camera_id}' not found"}

            if not await camera.is_connected():
                await camera.connect()

            stream_url = await camera.get_stream_url()
            if not stream_url:
                return {"success": False, "action": action, "error": f"Could not get stream URL for '{camera_id}'"}

            parsed = urlparse(stream_url)
            username = camera.config.params.get("username", "")
            password = camera.config.params.get("password", "")

            if username and password:
                auth_url = f"rtsp://{username}:{password}@{parsed.hostname}:{parsed.port or 554}{parsed.path}"
            else:
                auth_url = stream_url

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
