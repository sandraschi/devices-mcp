"""
Compatibility shims for pytapo dependencies.

This module patches kasa to provide compatibility with pytapo's expectations:
- kasa.transports module (imports from klaptransport)
- kasa.deviceconfig: DeviceConnectionParameters, DeviceEncryptionType, DeviceFamily (pytapo >= 3.4)
- AuthenticationError exception alias
- TPLinkSmartHomeProtocol (deprecated/removed in newer kasa versions)
"""

import sys


def _patch_kasa():
    """Patch kasa module for pytapo compatibility at sys.modules level."""
    # Create kasa.transports module in sys.modules BEFORE any imports
    if "kasa.transports" not in sys.modules:
        from types import ModuleType

        transports_module = ModuleType("kasa.transports")

        # Try to import from klaptransport, but don't fail if not available
        try:
            import kasa.klaptransport

            transports_module.KlapTransport = kasa.klaptransport.KlapTransport
            transports_module.KlapTransportV2 = kasa.klaptransport.KlapTransportV2
        except (ImportError, AttributeError):
            # Create dummy classes if klaptransport doesn't exist
            class DummyTransport:
                pass

            transports_module.KlapTransport = DummyTransport
            transports_module.KlapTransportV2 = DummyTransport

        transports_module.__all__ = ["KlapTransport", "KlapTransportV2"]

        # Add to sys.modules BEFORE any pytapo imports
        sys.modules["kasa.transports"] = transports_module

    # Patch kasa.deviceconfig for pytapo >= 3.4 (expects DeviceConnectionParameters, etc.)
    try:
        import kasa.deviceconfig as dc

        if not hasattr(dc, "DeviceConnectionParameters"):
            dc.DeviceConnectionParameters = dc.ConnectionType
        if not hasattr(dc, "DeviceEncryptionType"):
            dc.DeviceEncryptionType = dc.EncryptType
        if not hasattr(dc, "DeviceFamily"):
            dc.DeviceFamily = dc.DeviceFamilyType
    except (ImportError, AttributeError):
        pass

    # Patch TPLinkSmartHomeProtocol in kasa.protocol if it's missing
    try:
        import kasa.protocol

        if not hasattr(kasa.protocol, "TPLinkSmartHomeProtocol"):
            # Create a compatibility class that inherits from BaseProtocol
            class TPLinkSmartHomeProtocol(kasa.protocol.BaseProtocol):
                """Compatibility shim for deprecated TPLinkSmartHomeProtocol."""

                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)

            # Add to both the module and sys.modules
            kasa.protocol.TPLinkSmartHomeProtocol = TPLinkSmartHomeProtocol
            if "kasa.protocol" in sys.modules:
                sys.modules["kasa.protocol"].TPLinkSmartHomeProtocol = TPLinkSmartHomeProtocol
    except ImportError:
        pass

    # Patch DeviceError in kasa if it's missing (expected by pytapo >= 3.3.35)
    try:
        import kasa
        import kasa.exceptions

        if not hasattr(kasa, "DeviceError"):
            kasa.DeviceError = kasa.exceptions.SmartDeviceException

        # Add Device and SmartDevice aliases for pytapo compatibility
        if not hasattr(kasa, "Device"):
            kasa.Device = kasa.SmartDevice
        if not hasattr(kasa, "SmartDevice"):
            # If SmartDevice itself is missing (unlikely but safe), alias to something or pass
            pass

        # Also ensure it is in kasa.exceptions for consistency
        if not hasattr(kasa.exceptions, "DeviceError"):
            kasa.exceptions.DeviceError = kasa.exceptions.SmartDeviceException

        if not hasattr(kasa.exceptions, "AuthenticationError"):
            kasa.exceptions.AuthenticationError = kasa.exceptions.AuthenticationException
    except ImportError:
        pass


# Patch BEFORE any other imports in this module
_patch_kasa()
