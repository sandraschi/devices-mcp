import React, { useEffect, useRef, useState } from 'react';
import { PanelProps } from '@grafana/data';
import { PanelOptions } from './types';
import { css, cx } from '@emotion/css';
import { useStyles2 } from '@grafana/ui';
import Hls from 'hls.js';

interface Props extends PanelProps<PanelOptions> {}

export const TapoCameraPanel: React.FC<Props> = ({ options, width, height }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const styles = useStyles2(getStyles);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !options.streamUrl) {
      return;
    }

    let hls: Hls | null = null;

    const initPlayer = () => {
      if (options.streamType === 'hls') {
        if (Hls.isSupported()) {
          hls = new Hls({
            enableWorker: true,
            lowLatencyMode: true,
            backBufferLength: 0,
            maxBufferLength: 1,
            maxMaxBufferLength: 1,
            maxBufferSize: 6000000,
            maxBufferHole: 0.1,
          });

          hls.loadSource(options.streamUrl);
          hls.attachMedia(video);

          hls.on(Hls.Events.ERROR, (event, data) => {
            if (data.fatal) {
              switch (data.type) {
                case Hls.ErrorTypes.NETWORK_ERROR:
                  setError('Network error occurred');
                  hls?.recoverMediaError();
                  break;
                case Hls.ErrorTypes.MEDIA_ERROR:
                  setError('Media error occurred');
                  hls?.recoverMediaError();
                  break;
                default:
                  setError('Error loading stream');
                  break;
              }
            }
          });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
          // Native HLS support (Safari)
          video.src = options.streamUrl;
        } else {
          setError('HLS is not supported in this browser');
        }
      } else if (options.streamType === 'rtsp' || options.streamType === 'rtmp') {
        // RTSP/RTMP streams need to be proxied through a media server
        video.src = options.streamUrl;
      } else if (options.streamType === 'webrtc') {
        // WebRTC implementation would go here
        setError('WebRTC streaming is not yet implemented');
      } else if (options.streamType === 'mjpeg') {
        // MJPEG stream
        video.src = options.streamUrl;
      }

      // Handle authentication if needed
      if (options.useAuth && options.username && options.password) {
        // This is a simple approach - in a real app, you'd want to handle auth properly
        video.setAttribute('crossorigin', 'use-credentials');
        video.setAttribute('credentials', 'include');
      }

      // Auto-play if enabled
      if (options.autoPlay) {
        const playPromise = video.play();
        if (playPromise !== undefined) {
          playPromise
            .then(() => {
              setIsPlaying(true);
            })
            .catch((e) => {
              setError(`Auto-play failed: ${e.message}`);
            });
        }
      }
    };

    initPlayer();

    return () => {
      if (hls) {
        hls.destroy();
      }
      if (video) {
        video.pause();
        video.src = '';
      }
    };
  }, [options.streamUrl, options.streamType, options.useAuth, options.username, options.password, options.autoPlay]);

  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    if (video.paused) {
      video.play().catch(e => setError(`Failed to play: ${e.message}`));
      setIsPlaying(true);
    } else {
      video.pause();
      setIsPlaying(false);
    }
  };

  const handleFullscreen = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    if (video.requestFullscreen) {
      video.requestFullscreen();
    } else if ((video as any).webkitRequestFullscreen) {
      (video as any).webkitRequestFullscreen();
    } else if ((video as any).msRequestFullscreen) {
      (video as any).msRequestFullscreen();
    }
  };

  const handlePTZAction = (action: string) => {
    // In a real implementation, this would call your PTZ API
    console.log(`PTZ Action: ${action}`);
  };

  return (
    <div className={styles.container} style={{ width, height }}>
      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.videoContainer}>
        <video
          ref={videoRef}
          className={styles.video}
          controls={options.showControls}
          muted={options.muted}
          playsInline
        />

        {!options.showControls && (
          <div className={styles.customControls}>
            <button onClick={handlePlayPause} className={styles.controlButton}>
              {isPlaying ? '❚❚' : '▶'}
            </button>
            <button onClick={handleFullscreen} className={styles.controlButton}>
              ⛶
            </button>
          </div>
        )}
      </div>

      {options.showPtzControls && (
        <div className={styles.ptzControls}>
          <button onClick={() => handlePTZAction('up')}>⬆</button>
          <div>
            <button onClick={() => handlePTZAction('left')}>⬅</button>
            <button onClick={() => handlePTZAction('stop')}>⏹</button>
            <button onClick={() => handlePTZAction('right')}>➡</button>
          </div>
          <button onClick={() => handlePTZAction('down')}>⬇</button>
          <div className={styles.zoomControls}>
            <button onClick={() => handlePTZAction('zoomIn')}>+</button>
            <button onClick={() => handlePTZAction('zoomOut')}>-</button>
          </div>
        </div>
      )}
    </div>
  );
};

const getStyles = () => ({
  container: css`
    display: flex;
    flex-direction: column;
    height: 100%;
    position: relative;
    overflow: hidden;
  `,
  videoContainer: css`
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #1e1e1e;
  `,
  video: css`
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  `,
  customControls: css`
    position: absolute;
    bottom: 10px;
    left: 0;
    right: 0;
    display: flex;
    justify-content: center;
    gap: 10px;
    padding: 5px;
    background: rgba(0, 0, 0, 0.5);
  `,
  controlButton: css`
    background: none;
    border: none;
    color: white;
    font-size: 24px;
    cursor: pointer;
    padding: 5px 15px;
    border-radius: 4px;
    &:hover {
      background: rgba(255, 255, 255, 0.2);
    }
  `,
  ptzControls: css`
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 10px;
    background: #2b2b2b;
    gap: 5px;

    button {
      background: #3d3d3d;
      border: none;
      color: white;
      width: 40px;
      height: 40px;
      font-size: 20px;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;

      &:hover {
        background: #4a4a4a;
      }

      &:active {
        background: #5a5a5a;
      }
    }

    & > div {
      display: flex;
      gap: 5px;
    }
  `,
  zoomControls: css`
    margin-top: 10px;

    button {
      width: 30px;
      height: 30px;
      font-size: 16px;
    }
  `,
  error: css`
    position: absolute;
    top: 10px;
    left: 10px;
    right: 10px;
    padding: 10px;
    background: rgba(255, 0, 0, 0.7);
    color: white;
    border-radius: 4px;
    z-index: 10;
    text-align: center;
  `,
});
