"""Device control tools for Nest Protect MCP."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class HushAlarmParams(BaseModel):
    """Parameters for hushing an alarm."""

    device_id: str = Field(..., description="ID of the device to hush")
    duration_seconds: int = Field(
        180, ge=30, le=300, description="Duration to hush in seconds (30-300)"
    )


class SafetyCheckParams(BaseModel):
    """Parameters for running a safety check."""

    device_id: str = Field(..., description="ID of the device to test")
    test_type: Literal["full", "smoke", "co", "heat"] = Field(
        "full", description="Type of test to run"
    )


class LedBrightnessParams(BaseModel):
    """Parameters for setting LED brightness."""

    device_id: str = Field(..., description="ID of the device")
    brightness: int = Field(..., ge=0, le=100, description="Brightness level (0-100)")


class SoundAlarmParams(BaseModel):
    """Parameters for sounding an alarm for testing."""

    device_id: str = Field(..., description="ID of the device to test")
    alarm_type: Literal["smoke", "co", "security", "emergency"] = Field(
        "smoke", description="Type of alarm to sound"
    )
    duration_seconds: int = Field(
        10, ge=5, le=60, description="Duration to sound alarm in seconds (5-60)"
    )
    volume: int = Field(100, ge=50, le=100, description="Alarm volume percentage (50-100)")


class ArmDisarmParams(BaseModel):
    """Parameters for arming/disarming security system."""

    device_id: str = Field(..., description="ID of the security device (Nest Guard)")
    action: Literal["arm_home", "arm_away", "disarm"] = Field(
        ..., description="Security action to perform"
    )
    passcode: Optional[str] = Field(None, description="Security passcode (required for disarm)")


async def hush_alarm(device_id: str, duration_seconds: int = 180) -> Dict[str, Any]:
    """Silence an active alarm on a Nest Protect device."""
    import aiohttp

    from ..state_manager import get_app_state

    state = get_app_state()

    if not state.access_token:
        return {"status": "error", "message": "Not authenticated with Nest API"}

    try:
        url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices/{device_id}:executeCommand"
        headers = {"Authorization": f"Bearer {state.access_token}"}
        payload = {
            "command": "sdm.devices.commands.SafetyHush.Hush",
            "params": {"duration": f"{duration_seconds}s"},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    return {
                        "status": "success",
                        "message": f"Alarm hushed for {duration_seconds} seconds",
                        "device_id": device_id,
                    }
                error = await response.json()
                return {
                    "status": "error",
                    "message": "Failed to hush alarm",
                    "error": error.get("error", {}).get("message"),
                }
    except Exception as e:
        return {"status": "error", "message": f"Failed to hush alarm: {e!s}"}


async def run_safety_check(
    device_id: str, test_type: Literal["full", "smoke", "co", "heat"] = "full"
) -> Dict[str, Any]:
    """Run a safety check on a Nest Protect device."""
    import aiohttp

    from ..state_manager import get_app_state

    state = get_app_state()

    if not state.access_token:
        return {"status": "error", "message": "Not authenticated with Nest API"}

    try:
        url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices/{device_id}:executeCommand"
        headers = {"Authorization": f"Bearer {state.access_token}"}

        if test_type == "full":
            payload = {"command": "sdm.devices.commands.SafetyTest.SelfTest"}
        else:
            payload = {
                "command": "sdm.devices.commands.SafetyTest.SelfTest",
                "params": {"test_type": test_type.upper()},
            }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    return {
                        "status": "success",
                        "message": f"Started {test_type} safety test",
                        "device_id": device_id,
                    }
                error = await response.json()
                return {
                    "status": "error",
                    "message": "Failed to start safety test",
                    "error": error.get("error", {}).get("message"),
                }
    except Exception as e:
        return {"status": "error", "message": f"Failed to run safety test: {e!s}"}


async def set_led_brightness(device_id: str, brightness: int) -> Dict[str, Any]:
    """Set LED brightness for a Nest Protect device."""
    import aiohttp

    from ..state_manager import get_app_state

    state = get_app_state()

    if not state.access_token:
        return {"status": "error", "message": "Not authenticated with Nest API"}

    try:
        url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices/{device_id}:executeCommand"
        headers = {"Authorization": f"Bearer {state.access_token}"}
        payload = {
            "command": "sdm.devices.commands.Settings.LedBrightness",
            "params": {"level": brightness},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    return {
                        "status": "success",
                        "message": f"LED brightness set to {brightness}%",
                        "device_id": device_id,
                    }
                error = await response.json()
                return {
                    "status": "error",
                    "message": "Failed to set LED brightness",
                    "error": error.get("error", {}).get("message"),
                }
    except Exception as e:
        return {"status": "error", "message": f"Failed to set LED brightness: {e!s}"}


async def sound_alarm(
    device_id: str,
    alarm_type: Literal["smoke", "co", "security", "emergency"] = "smoke",
    duration_seconds: int = 10,
    volume: int = 100,
) -> Dict[str, Any]:
    """Sound an alarm on a Nest device for testing purposes."""
    import aiohttp

    from ..state_manager import get_app_state

    state = get_app_state()

    if not state.access_token:
        return {"status": "error", "message": "Not authenticated with Nest API"}

    try:
        url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices/{device_id}:executeCommand"
        headers = {"Authorization": f"Bearer {state.access_token}"}

        # Map alarm types to device commands
        command_mapping = {
            "smoke": "sdm.devices.commands.SafetyTest.SmokeAlarmTest",
            "co": "sdm.devices.commands.SafetyTest.CarbonMonoxideAlarmTest",
            "security": "sdm.devices.commands.SecurityTest.SecurityAlarmTest",
            "emergency": "sdm.devices.commands.SafetyTest.EmergencyAlarmTest",
        }

        if alarm_type not in command_mapping:
            return {"status": "error", "message": f"Invalid alarm type: {alarm_type}"}

        payload = {
            "command": command_mapping[alarm_type],
            "params": {"duration": f"{duration_seconds}s", "volume": volume},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    return {
                        "status": "success",
                        "message": f"⚠️ {alarm_type.upper()} alarm test started for {duration_seconds} seconds at {volume}% volume",
                        "device_id": device_id,
                        "alarm_type": alarm_type,
                        "duration": duration_seconds,
                        "volume": volume,
                        "warning": "🚨 LOUD ALARM WILL SOUND - Ensure occupants are aware this is a test!",
                    }
                error = await response.json()
                return {
                    "status": "error",
                    "message": "Failed to sound alarm",
                    "error": error.get("error", {}).get("message"),
                }
    except Exception as e:
        return {"status": "error", "message": f"Failed to sound alarm: {e!s}"}


async def arm_disarm_security(
    device_id: str,
    action: Literal["arm_home", "arm_away", "disarm"],
    passcode: Optional[str] = None,
) -> Dict[str, Any]:
    """Arm or disarm Nest security system (Nest Guard/Secure)."""
    import aiohttp

    from ..state_manager import get_app_state

    state = get_app_state()

    if not state.access_token:
        return {"status": "error", "message": "Not authenticated with Nest API"}

    if action == "disarm" and not passcode:
        return {
            "status": "error",
            "message": "Passcode required for disarming security system",
        }

    try:
        url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices/{device_id}:executeCommand"
        headers = {"Authorization": f"Bearer {state.access_token}"}

        # Map actions to device commands
        command_mapping = {
            "arm_home": "sdm.devices.commands.SecuritySystem.ArmHome",
            "arm_away": "sdm.devices.commands.SecuritySystem.ArmAway",
            "disarm": "sdm.devices.commands.SecuritySystem.Disarm",
        }

        payload = {"command": command_mapping[action]}

        if action == "disarm" and passcode:
            payload["params"] = {"passcode": passcode}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    action_messages = {
                        "arm_home": "🏠 Security system armed for HOME mode",
                        "arm_away": "🚗 Security system armed for AWAY mode",
                        "disarm": "✅ Security system disarmed",
                    }

                    return {
                        "status": "success",
                        "message": action_messages[action],
                        "device_id": device_id,
                        "action": action,
                        "timestamp": "timestamp_placeholder",  # Would be filled by actual API response
                    }
                error = await response.json()
                return {
                    "status": "error",
                    "message": f"Failed to {action} security system",
                    "error": error.get("error", {}).get("message"),
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to {action} security system: {e!s}",
        }
