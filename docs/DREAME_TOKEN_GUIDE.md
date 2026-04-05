# Dreame D20 Pro Token Extraction Guide (mii stack)

To integrate your Dreame D20 Pro with the Devices MCP and Home Assistant, you need to extract the Miio token.

## Recommended Tools (The "Mii Stack")

1. **Xiaomi Cloud Tokens Extractor** (SOTA Method)
   - Repository: [PiotrMachowski/Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor)
   - This works for devices bound to your Xiaomi account.

### Can we get the D20 Pro API key (Local Token)?

**Short answer: NO.**

The Dreame D20 Pro is a newer, Dreamehome-exclusive device. Unlike older Xiaomi-branded models, it does not store a local token that can be easily extracted using standard tools (like the Xiaomi Cloud Token Extractor).

## How to Integrate the D20 Pro?

**Solution: YES (via Cloud Integration).**

You should use the **Home Assistant Dreame Vacuum Custom Component**. This integration allows you to log in with your **Dreamehome account credentials** (Alibaba Cloud based) directly.

1.  **Setup Home Assistant**: If not already done.
2.  **Install Custom Component**: Use HACS to install `Dreame Vacuum`.
3.  **Login**: Use your Dreamehome email/phone and password.
4.  **Devices MCP Integration**: Our `DreameClient` is already designed to talk to Home Assistant's REST API.

## Step-by-Step Instructions

1. **Check App Compatibility**: If the D20 Pro is not in the Xiaomi Mi Home app (iOS), use the **Dreamehome** app.
2. **Use Cloud Integration**: In Home Assistant, install the `dreame_vacuum` integration and choose the "Dreamehome Account" option during setup.
3. **Configure Devices MCP**: Point the MCP to your Home Assistant instance.


## Configuration Example

### .env
```env
DREAME_VACUUM_HOST=192.168.0.144
DREAME_VACUUM_TOKEN=your_extracted_token_here
```

### config.yaml
```yaml
robotics:
  dreame_d20:
    type: dreame
    host: 192.168.0.144
    token: ${DREAME_VACUUM_TOKEN}
```
