# Secrets Management Guide

**Last Updated:** 2025-12-02
**Status:** Current Implementation + Improvement Plan

---

## Current Implementation

### 🔴 **Outside Docker (Host)**

**Storage Method:** Plain text in `config.yaml` file

**Location:** `D:\Dev\repos\devices-mcp\config.yaml`

**How Secrets Are Retrieved:**
1. `ConfigManager.load_config()` reads `config.yaml` directly
2. Secrets are accessed via `get_config()` or `get_model()` functions
3. **No environment variable override** (except `ENABLE_MOCK_ENERGY`)

**Example from `config.yaml`:**
```yaml
cameras:
  kitchen_cam:
    params:
      username: sandraschi
      password: Sec1000kitchen  # ⚠️ Plain text

energy:
  tapo_p115:
    account:
      email: sandraschipal@hotmail.com
      password: Sec0860ta#  # ⚠️ Plain text

weather:
  integrations:
    netatmo:
      client_secret: 'Uge1m7YrypuK2Wz7QjqfhduhEQlPJYWC4uKSEH'  # ⚠️ Plain text
      refresh_token: '5ca3ae420ec7040a008b57dd|...'  # ⚠️ Plain text

ring:
  email: sandraschipal@hotmail.com
  password: "Sec1000ri#"  # ⚠️ Plain text

security:
  integrations:
    homeassistant:
      access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # ⚠️ Plain text
```

**Code Flow:**
```python
# src/devices_mcp/config/__init__.py
config_manager = ConfigManager()
config = config_manager.load_config()  # Reads config.yaml directly
```

---

### 🟡 **Inside Docker**

**Storage Method:** Mixed approach (partially implemented)

**1. Environment Variables (Declared but NOT Used):**
```yaml
# docker-compose.yml
environment:
  - RING_USERNAME=${RING_USERNAME:-}
  - RING_PASSWORD=${RING_PASSWORD:-}
  - HUE_BRIDGE_IP=${HUE_BRIDGE_IP:-}
  - HUE_USERNAME=${HUE_USERNAME:-}
  - TAPO_USERNAME=${TAPO_USERNAME:-}
  - TAPO_PASSWORD=${TAPO_PASSWORD:-}
```

**⚠️ Problem:** These environment variables are **declared but never read** by the application code!

**2. Config File Mount (Currently Used):**
```yaml
volumes:
  - ./config.yaml:/app/config.yaml:ro  # Mounts host config.yaml into container
```

**How Secrets Are Retrieved:**
- Same as host: reads from mounted `config.yaml` file
- Environment variables are **ignored** by the code

**3. Docker Secrets (NOT Implemented):**
- No Docker Swarm secrets support
- No Docker Compose secrets support

---

## Security Issues

### ❌ **Current Problems:**

1. **Plain Text Secrets in Git:**
   - `config.yaml` contains passwords, tokens, API keys in plain text
   - Risk: If repo is pushed to Git, secrets are exposed

2. **No Environment Variable Override:**
   - Docker environment variables are declared but unused
   - Can't override secrets without editing `config.yaml`

3. **No `.env` File Support:**
   - No `.env` file loading (unlike other MCP servers)
   - No `.env.example` template

4. **No Secret Rotation:**
   - No mechanism to rotate secrets without editing files
   - No audit trail for secret access

5. **No Encryption:**
   - No encrypted storage (no `sops`, no Vault integration)
   - No keyring/keychain support

---

## Recommended Improvements

### ✅ **Phase 1: Environment Variable Support (Quick Win)**

**Priority:** High
**Effort:** Low
**Impact:** High

**Implementation:**

1. **Update `ConfigManager` to check environment variables first:**
```python
# src/devices_mcp/config/__init__.py
import os
from dotenv import load_dotenv

class ConfigManager:
    def load_config(self) -> Dict[str, Any]:
        # Load .env file if present
        load_dotenv()

        # Load config.yaml
        config = yaml.safe_load(f)

        # Override with environment variables
        env_overrides = {
            # Ring
            "ring.email": os.getenv("RING_EMAIL"),
            "ring.password": os.getenv("RING_PASSWORD"),

            # Tapo
            "energy.tapo_p115.account.email": os.getenv("TAPO_EMAIL"),
            "energy.tapo_p115.account.password": os.getenv("TAPO_PASSWORD"),

            # Netatmo
            "weather.integrations.netatmo.client_id": os.getenv("NETATMO_CLIENT_ID"),
            "weather.integrations.netatmo.client_secret": os.getenv("NETATMO_CLIENT_SECRET"),
            "weather.integrations.netatmo.refresh_token": os.getenv("NETATMO_REFRESH_TOKEN"),

            # Hue
            "lighting.philips_hue.bridge_ip": os.getenv("HUE_BRIDGE_IP"),
            "lighting.philips_hue.username": os.getenv("HUE_USERNAME"),

            # Home Assistant
            "security.integrations.homeassistant.access_token": os.getenv("HA_ACCESS_TOKEN"),

            # Camera credentials (per-camera)
            # Note: This requires special handling for nested camera configs
        }

        # Apply overrides (skip None values)
        for key, value in env_overrides.items():
            if value is not None:
                self._set_nested(config, key, value)

        return config
```

2. **Create `.env.example` template:**
```bash
# .env.example
# Copy this to .env and fill in your secrets
# DO NOT commit .env to Git!

# Ring Doorbell
RING_EMAIL=your-email@example.com
RING_PASSWORD=your-password

# Tapo P115 Smart Plugs
TAPO_EMAIL=your-email@example.com
TAPO_PASSWORD=your-password

# Netatmo Weather
NETATMO_CLIENT_ID=your-client-id
NETATMO_CLIENT_SECRET=your-client-secret
NETATMO_REFRESH_TOKEN=your-refresh-token

# Philips Hue
HUE_BRIDGE_IP=192.168.0.83
HUE_USERNAME=your-hue-username

# Home Assistant
HA_ACCESS_TOKEN=your-long-lived-access-token

# Camera Credentials (per-camera, use camera name as prefix)
CAMERA_KITCHEN_CAM_USERNAME=your-username
CAMERA_KITCHEN_CAM_PASSWORD=your-password
CAMERA_LIVING_ROOM_CAM_USERNAME=your-username
CAMERA_LIVING_ROOM_CAM_PASSWORD=your-password
```

3. **Update `.gitignore`:**
```gitignore
# Secrets
.env
config.local.yaml
*.secret.yaml
```

4. **Update Docker Compose to use `.env` file:**
```yaml
# docker-compose.yml
services:
  dashboard:
    env_file:
      - .env  # Load secrets from .env file
    environment:
      # Fallback to environment variables if .env not present
      - RING_EMAIL=${RING_EMAIL:-}
      - RING_PASSWORD=${RING_PASSWORD:-}
      # ... etc
```

---

### ✅ **Phase 2: Docker Secrets Support (Production)**

**Priority:** Medium
**Effort:** Medium
**Impact:** High (for production deployments)

**Implementation:**

1. **Use Docker Compose Secrets (Docker Compose 3.8+):**
```yaml
# docker-compose.yml
services:
  dashboard:
    secrets:
      - ring_password
      - tapo_password
      - netatmo_client_secret
      - netatmo_refresh_token
      - ha_access_token
    environment:
      - RING_PASSWORD_FILE=/run/secrets/ring_password
      - TAPO_PASSWORD_FILE=/run/secrets/tapo_password
      # ... etc

secrets:
  ring_password:
    file: ./secrets/ring_password.txt
  tapo_password:
    file: ./secrets/tapo_password.txt
  netatmo_client_secret:
    file: ./secrets/netatmo_client_secret.txt
  netatmo_refresh_token:
    file: ./secrets/netatmo_refresh_token.txt
  ha_access_token:
    file: ./secrets/ha_access_token.txt
```

2. **Update code to read from secret files:**
```python
def get_secret_from_file(env_var_name: str) -> Optional[str]:
    """Read secret from file if env var points to a file path."""
    file_path = os.getenv(env_var_name)
    if file_path and file_path.endswith("_FILE"):
        # Remove _FILE suffix to get base env var name
        base_name = env_var_name.replace("_FILE", "")
        file_path = os.getenv(env_var_name)
        if file_path and Path(file_path).exists():
            return Path(file_path).read_text().strip()
    return None
```

---

### ✅ **Phase 3: Encrypted Secrets (Advanced)**

**Priority:** Low
**Effort:** High
**Impact:** High (for enterprise/security-critical deployments)

**Options:**

1. **Mozilla SOPS (Secrets OPerationS):**
   - Encrypt `config.yaml` with age/PGP keys
   - Decrypt at runtime
   - Git-safe (encrypted files can be committed)

2. **HashiCorp Vault:**
   - Centralized secret management
   - Dynamic secrets, rotation, audit logging
   - Requires Vault server

3. **1Password CLI:**
   - Integration with 1Password vault
   - CLI-based secret retrieval
   - Good for personal/team use

4. **System Keyring:**
   - Windows Credential Manager
   - macOS Keychain
   - Linux Secret Service (GNOME) / KWallet (KDE)

---

## Migration Path

### **Step 1: Create `.env.example` (No Code Changes)**
- Document all required secrets
- Add to `.gitignore`

### **Step 2: Add Environment Variable Support**
- Update `ConfigManager` to check `os.getenv()` first
- Add `python-dotenv` dependency
- Test with `.env` file

### **Step 3: Update Docker Compose**
- Use `env_file: .env`
- Keep environment variable fallbacks

### **Step 4: Remove Secrets from `config.yaml`**
- Move all secrets to `.env`
- Keep `config.yaml` for non-sensitive config
- Add `config.yaml.example` template

### **Step 5: (Optional) Add Docker Secrets**
- For production deployments
- Use Docker Compose secrets

### **Step 6: (Optional) Add Encryption**
- Implement SOPS or Vault integration
- For enterprise/security-critical use cases

---

## Quick Reference

### **Current State (Outside Docker):**
```bash
# Secrets stored in:
config.yaml  # Plain text, in repo root

# How to use:
# Edit config.yaml directly
# Restart server
```

### **Current State (Inside Docker):**
```bash
# Secrets stored in:
config.yaml  # Mounted from host (read-only)

# Environment variables:
# Declared but NOT used by code

# How to use:
# Edit config.yaml on host
# Restart container
```

### **Recommended (After Phase 1):**
```bash
# Secrets stored in:
.env  # Not in Git, loaded at runtime

# Config stored in:
config.yaml  # Non-sensitive config only

# How to use:
# Copy .env.example to .env
# Fill in secrets
# Restart server/container
```

---

## Security Best Practices

1. **Never commit secrets to Git:**
   - Use `.gitignore` for `.env` and `config.local.yaml`
   - Use `git-secrets` or `truffleHog` to scan commits

2. **Use least privilege:**
   - Don't share secrets between services unnecessarily
   - Use service-specific credentials when possible

3. **Rotate secrets regularly:**
   - Quarterly for service accounts
   - Immediately after any security incident

4. **Audit secret access:**
   - Log when secrets are loaded (not the values!)
   - Monitor for unauthorized access

5. **Use encrypted storage in production:**
   - SOPS, Vault, or similar for production
   - Never store production secrets in plain text

---

## Related Files

- `config.yaml` - Current secrets storage (plain text)
- `src/devices_mcp/config/__init__.py` - Config loading logic
- `docker-compose.yml` - Docker environment variables (unused)
- `docs/mcp-technical/SECRETS_HARDENING_PLAN.md` - Original plan

---

**Next Steps:**
1. Implement Phase 1 (Environment Variable Support)
2. Create `.env.example` template
3. Update documentation
4. Test with Docker and host deployments
