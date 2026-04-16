/**
 * Fleet Hub Configuration
 * 
 * Update HUB_IP to your PC's local IP address (e.g., from 'ipconfig' on Windows).
 * Ensure your iPhone and PC are on the same Wi-Fi network.
 */

export const CONFIG = {
  // Replace with your PC's local IP
  HUB_IP: '192.168.1.50',
  HUB_PORT: '10716',
  
  get API_BASE_URL() {
    return `http://${this.HUB_IP}:${this.HUB_PORT}/api`;
  },
  
  // Heartbeat threshold (minutes) to consider a node 'offline'
  OFFLINE_THRESHOLD: 10,
};
