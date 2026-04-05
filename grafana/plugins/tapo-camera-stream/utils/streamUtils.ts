import Hls from 'hls.js';

/**
 * Initialize HLS.js player with proper configuration
 */
export const initHLS = (video: HTMLVideoElement, url: string, onError: (error: string) => void) => {
  if (Hls.isSupported()) {
    const hls = new Hls({
      enableWorker: true,
      lowLatencyMode: true,
      backBufferLength: 0,
      maxBufferLength: 1,
      maxMaxBufferLength: 2,
      maxBufferSize: 10 * 1000 * 1000,
      maxBufferHole: 0.5,
      xhrSetup: (xhr, _url) => {
        // Add authentication headers if needed
        // const { username, password } = getAuthInfo();
        // if (username && password) {
        //   const credentials = btoa(`${username}:${password}`);
        //   xhr.setRequestHeader('Authorization', `Basic ${credentials}`);
        // }
      },
    });

    hls.loadSource(url);
    hls.attachMedia(video);

    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      // Auto-quality selection based on available levels
      if (hls.levels.length > 1) {
        // Select the highest quality by default
        hls.currentLevel = hls.levels.length - 1;
      }
    });

    hls.on(Hls.Events.ERROR, (event, data) => {
      if (data.fatal) {
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            hls.startLoad();
            break;
          case Hls.ErrorTypes.MEDIA_ERROR:
            hls.recoverMediaError();
            break;
          default:
            onError(`HLS Error: ${data.details}`);
            break;
        }
      }
    });

    return hls;
  }
  return null;
};

/**
 * Initialize WebRTC connection for camera stream
 */
export const initWebRTC = async (
  video: HTMLVideoElement,
  url: string,
  onError: (error: string) => void
): Promise<RTCPeerConnection | null> => {
  try {
    // This is a simplified example - in a real implementation, you'd need to handle signaling
    const peerConnection = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        // Add TURN servers if needed
      ],
    });

    // Handle incoming tracks
    peerConnection.ontrack = (event) => {
      if (event.streams && event.streams[0]) {
        video.srcObject = event.streams[0];
      } else {
        const stream = new MediaStream();
        stream.addTrack(event.track);
        video.srcObject = stream;
      }
    };

    // Handle ICE candidates
    peerConnection.onicecandidate = (event) => {
      // In a real implementation, send the candidate to the signaling server
      if (event.candidate) {
        // signalingService.sendCandidate(event.candidate);
      }
    };

    // Create and set local description
    const offer = await peerConnection.createOffer({
      offerToReceiveVideo: true,
      offerToReceiveAudio: true,
    });
    await peerConnection.setLocalDescription(offer);

    // In a real implementation, you would send the offer to a signaling server
    // and receive an answer
    // const answer = await signalingService.sendOffer(offer);
    // await peerConnection.setRemoteDescription(answer);

    return peerConnection;
  } catch (error) {
    onError(`WebRTC Error: ${error.message}`);
    return null;
  }
};

/**
 * Get stream URL with authentication if needed
 */
export const getAuthenticatedUrl = (
  url: string,
  username?: string,
  password?: string
): string => {
  if (!username || !password) {
    return url;
  }

  try {
    const parsedUrl = new URL(url);
    parsedUrl.username = username;
    parsedUrl.password = password;
    return parsedUrl.toString();
  } catch (error) {
    console.error('Invalid URL:', error);
    return url;
  }
};

/**
 * Get supported stream types based on browser capabilities
 */
export const getSupportedStreamTypes = (): string[] => {
  const video = document.createElement('video');
  const supported: string[] = [];

  // Check HLS support
  if (Hls.isSupported() || video.canPlayType('application/vnd.apple.mpegurl')) {
    supported.push('hls');
  }

  // Check MJPEG support
  if (video.canPlayType('image/jpeg')) {
    supported.push('mjpeg');
  }

  // WebRTC is generally supported in modern browsers
  supported.push('webrtc');

  // RTSP/RTMP typically require a proxy or conversion
  // These are included but may not work directly in all browsers
  supported.push('rtsp', 'rtmp');

  return supported;
};

/**
 * Get the best available stream type based on browser support
 */
export const getBestStreamType = (availableTypes: string[]): string | null => {
  const supportedTypes = getSupportedStreamTypes();

  // Prefer HLS > WebRTC > MJPEG > RTSP > RTMP
  const priorityOrder = ['hls', 'webrtc', 'mjpeg', 'rtsp', 'rtmp'];

  for (const type of priorityOrder) {
    if (availableTypes.includes(type) && supportedTypes.includes(type)) {
      return type;
    }
  }

  return availableTypes.length > 0 ? availableTypes[0] : null;
};
