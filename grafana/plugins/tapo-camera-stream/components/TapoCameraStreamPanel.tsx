import React, { useEffect, useRef, useState, useCallback } from 'react';
import { PanelProps } from '@grafana/data';
import { SimpleOptions } from '../types';
import { css, cx } from '@emotion/css';
import { useTheme2, stylesFactory } from '@grafana/ui';
import Hls from 'hls.js';
import { initHLS, initWebRTC, getAuthenticatedUrl } from '../utils/streamUtils';

interface Props extends PanelProps<SimpleOptions> {}

export const TapoCameraStreamPanel: React.FC<Props> = ({ options, data, width, height }) => {
  const theme = useTheme2();
  const styles = getStyles(theme);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(options.muted ?? true);
  const [streamInfo, setStreamInfo] = useState({
    bitrate: 0,
    resolution: { width: 0, height: 0 },
    codec: '',
    loaded: false,
    loading: false,
    error: null as string | null,
  });

  const hlsRef = useRef<Hls | null>(null);
  const webrtcRef = useRef<RTCPeerConnection | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout>();

  // Handle stream errors with retry logic
  const handleStreamError = useCallback((errorMessage: string, isFatal = false) => {
    setError(errorMessage);
    setStreamInfo(prev => ({
      ...prev,
      error: errorMessage,
      loading: false,
      loaded: false,
    }));

    if (isFatal && options.autoReconnect) {
      // Auto-retry after delay
      const retryDelay = 5000; // 5 seconds
      retryTimeoutRef.current = setTimeout(() => {
        setError(null);
        initializeStream();
      }, retryDelay);
    }
  }, [options.autoReconnect]);

  // Initialize video player and load stream
  const initializeStream = useCallback(async () => {
    const video = videoRef.current;
    if (!video || !options.streamUrl) {
      return;
    }

    // Cleanup previous instances
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }

    if (webrtcRef.current) {
      webrtcRef.current.close();
      webrtcRef.current = null;
    }

    // Clear any pending retries
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = undefined;
    }

    setStreamInfo(prev => ({
      ...prev,
      loading: true,
      loaded: false,
      error: null,
    }));

    try {
      const streamUrl = options.useAuth
        ? getAuthenticatedUrl(options.streamUrl, options.username, options.password)
        : options.streamUrl;

      // Handle different stream types
      if (options.streamType === 'hls') {
        const hls = initHLS(video, streamUrl, (error) => {
          handleStreamError(error, true);
        });

        if (hls) {
          hlsRef.current = hls;
          hls.on(Hls.Events.MANIFEST_PARSED, () => {
            setStreamInfo(prev => ({
              ...prev,
              loaded: true,
              loading: false,
            }));

            if (options.autoPlay) {
              video.play().catch(e => {
                handleStreamError(`Auto-play failed: ${e.message}`);
              });
            }
          });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
          // Safari native HLS
          video.src = streamUrl;
          setStreamInfo(prev => ({ ...prev, loaded: true, loading: false }));

          if (options.autoPlay) {
            video.play().catch(e => {
              handleStreamError(`Auto-play failed: ${e.message}`);
            });
          }
        } else {
          handleStreamError('HLS is not supported in this browser', false);
        }
      }
      else if (options.streamType === 'webrtc') {
        const pc = await initWebRTC(video, streamUrl, (error) => {
          handleStreamError(error, true);
        });

        if (pc) {
          webrtcRef.current = pc;
          setStreamInfo(prev => ({
            ...prev,
            loaded: true,
            loading: false,
          }));
        }
      }
      else {
        // For MJPEG, RTSP, RTMP (handled by browser or external player)
        video.src = streamUrl;
        video.muted = options.muted ?? true;

        setStreamInfo(prev => ({
          ...prev,
          loaded: true,
          loading: false,
        }));

        const canAutoplay = options.streamType === 'mjpeg';
        if (options.autoPlay && canAutoplay) {
          video.play().catch(e => {
            handleStreamError(`Auto-play failed: ${e.message}`);
          });
        }
      }
    } catch (error) {
      handleStreamError(`Failed to initialize stream: ${error.message}`, true);
    }
  }, [options, handleStreamError]);

  // Initialize stream when component mounts or options change
  useEffect(() => {
    initializeStream();

    // Cleanup on unmount
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }

      if (webrtcRef.current) {
        webrtcRef.current.close();
        webrtcRef.current = null;
      }

      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = undefined;
      }
    };
  }, [initializeStream]);

    // Handle video events
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleError = () => {
      if (video.error) {
        setError(`Video error: ${video.error.message}`);
      }
    };

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('error', handleError);

    initVideo();

    // Cleanup
    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('error', handleError);

      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
    };
  }, [options.streamUrl, options.streamType, options.autoPlay, options.muted]);

  // Handle play/pause
  const togglePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      video.play().catch(e => {
        setError(`Play failed: ${e.message}`);
      });
    } else {
      video.pause();
    }
  };

  // Handle mute/unmute
  const toggleMute = () => {
    const video = videoRef.current;
    if (video) {
      video.muted = !video.muted;
      setIsMuted(video.muted);
    }
  };

  // Calculate dimensions
  const maxWidth = options.maxWidth > 0 ? Math.min(options.maxWidth, width) : width;
  const aspectRatio = streamInfo.resolution.width && streamInfo.resolution.height
    ? streamInfo.resolution.width / streamInfo.resolution.height
    : 16 / 9; // Default to 16:9 if resolution not available
  const videoHeight = maxWidth / aspectRatio;

  // Render stream info
  const renderStreamInfo = () => {
    if (!options.debug) {
      return null;
    }

    return (
      <div className={styles.debugInfo}>
        <div>Status: {streamInfo.loading ? 'Loading...' : streamInfo.loaded ? 'Loaded' : 'Not Loaded'}</div>
        {streamInfo.error && <div>Error: {streamInfo.error}</div>}
        {streamInfo.bitrate > 0 && (
          <div>Bitrate: {(streamInfo.bitrate / 1024).toFixed(2)} Kbps</div>
        )}
        {streamInfo.resolution.width > 0 && (
          <div>
            Resolution: {streamInfo.resolution.width}×{streamInfo.resolution.height}
          </div>
        )}
        {streamInfo.codec && <div>Codec: {streamInfo.codec}</div>}
      </div>
    );
  };

  return (
    <div className={styles.container} style={{ width, height }}>
      {error ? (
        <div className={styles.error}>
          <p>{error}</p>
          <div className={styles.buttonGroup}>
            <button onClick={() => setError(null)} className={styles.retryButton}>
              Retry
            </button>
            <button onClick={initializeStream} className={styles.retryButton}>
              Reconnect
            </button>
          </div>
        </div>
      ) : streamInfo.loading ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <p>Connecting to stream...</p>
        </div>
      ) : (
        <>
          <div className={styles.videoContainer} style={{ maxWidth }}>
            <video
              ref={videoRef}
              className={styles.video}
              style={{ height: videoHeight }}
              playsInline
              muted={options.muted}
              controls={options.showControls}
              onLoadedMetadata={(e) => {
                const video = e.target as HTMLVideoElement;
                setStreamInfo(prev => ({
                  ...prev,
                  resolution: {
                    width: video.videoWidth,
                    height: video.videoHeight,
                  },
                  loaded: true,
                  loading: false,
                }));
              }}
            />

            {options.showControls && (
              <div className={styles.controls}>
                <div className={styles.controlGroup}>
                  <button
                    onClick={togglePlayPause}
                    className={styles.controlButton}
                    title={isPlaying ? 'Pause' : 'Play'}
                  >
                    {isPlaying ? '❚❚' : '▶'}
                  </button>
                  <button
                    onClick={toggleMute}
                    className={styles.controlButton}
                    title={isMuted ? 'Unmute' : 'Mute'}
                  >
                    {isMuted ? '🔇' : '🔊'}
                  </button>
                </div>

                <div className={styles.streamInfo}>
                  {options.streamType.toUpperCase()}
                  {streamInfo.resolution.width > 0 && (
                    <span className={styles.streamQuality}>
                      {streamInfo.resolution.width}×{streamInfo.resolution.height}
                    </span>
                  )}
                  {streamInfo.bitrate > 0 && (
                    <span className={styles.streamBitrate}>
                      {(streamInfo.bitrate / 1024).toFixed(0)}kbps
                    </span>
                  )}
                </div>

                <div className={styles.controlGroup}>
                  <button
                    onClick={initializeStream}
                    className={styles.controlButton}
                    title="Reconnect"
                  >
                    🔄
                  </button>
                </div>
              </div>
            )}

            {renderStreamInfo()}
          </div>

          {!options.streamUrl && (
            <div className={styles.placeholder}>
              <p>No stream URL configured</p>
              <p>Please set the stream URL in the panel options</p>
            </div>
          )}
        </>
      )}
    </div>
  );
};

const getStyles = stylesFactory((theme) => ({
  container: css`
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: ${theme.spacing(1)};
    height: 100%;
    overflow: auto;
  `,
  videoContainer: css`
    position: relative;
    width: 100%;
    background-color: ${theme.colors.background.primary};
    border-radius: ${theme.shape.borderRadius()};
    overflow: hidden;
    box-shadow: ${theme.shadows.z1};
  `,
  video: css`
    display: block;
    width: 100%;
    background-color: #000;
  `,
  controls: css`
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: ${theme.spacing(0.5, 1)};
    background-color: ${theme.isDark ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.9)'};
    border-top: 1px solid ${theme.colors.border.weak};
    position: relative;
    z-index: 1;
  `,
  controlButton: css`
    background: none;
    border: none;
    color: ${theme.colors.text.primary};
    font-size: ${theme.typography.h4.fontSize};
    cursor: pointer;
    padding: ${theme.spacing(0.5, 1)};
    border-radius: ${theme.shape.borderRadius()};
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;

    &:hover {
      background-color: ${theme.colors.action.hover};
      transform: scale(1.1);
    }

    &:active {
      transform: scale(0.95);
    }

    &:focus {
      outline: none;
      box-shadow: 0 0 0 2px ${theme.colors.primary.main};
    }

    &[disabled] {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none !important;
    }
  `,

  controlGroup: css`
    display: flex;
    align-items: center;
    gap: ${theme.spacing(0.5)};
  `,
  streamInfo: css`
    flex-grow: 1;
    font-size: ${theme.typography.bodySmall.fontSize};
    color: ${theme.colors.text.secondary};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: flex;
    align-items: center;
    gap: ${theme.spacing(2)};
    padding: 0 ${theme.spacing(1)};

    @media (max-width: 600px) {
      display: none;
    }
  `,

  streamQuality: css`
    background: ${theme.colors.background.secondary};
    border-radius: ${theme.shape.borderRadius(1)};
    padding: ${theme.spacing(0.25, 1)};
    font-size: ${theme.typography.bodySmall.fontSize};
    margin-left: ${theme.spacing(1)};
  `,

  streamBitrate: css`
    color: ${theme.colors.text.disabled};
    font-size: ${theme.typography.bodySmall.fontSize};
  `,
  error: css`
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: ${theme.colors.error.text};
    background-color: ${theme.colors.error.main};
    padding: ${theme.spacing(2)};
    border-radius: ${theme.shape.borderRadius()};
    text-align: center;
    max-width: 80%;
  `,
  retryButton: css`
    margin-top: ${theme.spacing(2)};
    padding: ${theme.spacing(0.5, 2)};
    background-color: ${theme.colors.error.contrastText};
    color: ${theme.colors.error.main};
    border: none;
    border-radius: ${theme.shape.borderRadius()};
    cursor: pointer;

    &:hover {
      opacity: 0.9;
    }
  `,
  loading: css`
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: ${theme.colors.text.secondary};

    .${css`
      width: 40px;
      height: 40px;
      border: 4px solid ${theme.colors.border.weak};
      border-top-color: ${theme.colors.primary.main};
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: ${theme.spacing(2)};

      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `} {}
  `,

  placeholder: css`
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: ${theme.colors.text.secondary};
    font-style: italic;
    text-align: center;
    padding: ${theme.spacing(4)};
  `,

  debugInfo: css`
    position: absolute;
    bottom: 40px;
    left: 0;
    right: 0;
    background: rgba(0, 0, 0, 0.7);
    color: #fff;
    font-size: ${theme.typography.bodySmall.fontSize};
    padding: ${theme.spacing(1)};
    font-family: ${theme.typography.fontFamilyMonospace};
  `,

  buttonGroup: css`
    display: flex;
    gap: ${theme.spacing(1)};
    margin-top: ${theme.spacing(2)};
  `,
}));
