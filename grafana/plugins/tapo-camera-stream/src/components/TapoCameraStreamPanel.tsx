import React, { useRef, useEffect, useState } from 'react';
import { PanelProps, InterpolateFunction, AbsoluteTimeRange } from '@grafana/data';
import { SimpleOptions } from '../../types';
import { css } from '@emotion/css';
import { useStyles2 } from '@grafana/ui';

// Extend the base PanelProps with our custom SimpleOptions
type Props = PanelProps<SimpleOptions> & {
  // Optional event handlers specific to our panel
  onFieldOptionsChange?: (options: any) => void;
  onFieldOverrideOptionsChange?: (options: any) => void;
  onFieldConfigEditorMount?: (editor: any) => void;
  onFieldConfigEditorUnmount?: () => void;
  onPanelConfigEditorMount?: (editor: any) => void;
  onPanelConfigEditorUnmount?: () => void;
};

const getStyles = () => ({
  wrapper: css`
    font-family: Open Sans;
    position: relative;
  `,
  video: css`
    width: 100%;
    height: 100%;
    object-fit: contain;
  `,
  controls: css`
    position: absolute;
    bottom: 10px;
    left: 10px;
    right: 10px;
    display: flex;
    justify-content: center;
    gap: 10px;
    padding: 10px;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 4px;
  `,
  button: css`
    background: #1f60c4;
    color: white;
    border: none;
    padding: 5px 10px;
    border-radius: 3px;
    cursor: pointer;
    &:hover {
      background: #1a4b8c;
    }
  `,
});

export const TapoCameraStreamPanel: React.FC<Props> = ({
  // Required props from PanelProps<SimpleOptions>
  options,
  width,
  height,

  // Other props we might use
  data,
  timeRange,
  timeZone,

  // Event handlers we might use
  onOptionsChange,

  // Rest props
  ...rest
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const styles = useStyles2(getStyles);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    document.addEventListener('fullscreenchange', handleFullscreenChange);

    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  };

  const toggleFullscreen = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    if (!document.fullscreenElement) {
      video.requestFullscreen().catch(err => {
        console.error(`Error attempting to enable fullscreen: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  };

  const getStreamSource = () => {
    if (!options.streamUrl) {
      return null;
    }

    switch (options.streamType) {
      case 'hls':
        return (
          <source
            src={options.streamUrl}
            type={options.streamUrl.includes('m3u8') ? 'application/x-mpegURL' : 'application/vnd.apple.mpegurl'}
          />
        );
      case 'rtsp':
      case 'rtmp':
        // Note: RTSP/RTMP typically requires a media server or MSE implementation
        // This is a simplified example - you might need a more robust solution
        return <source src={options.streamUrl} type={`video/${options.streamType}`} />;
      case 'webrtc':
        // WebRTC implementation would go here
        return null;
      case 'mjpeg':
        return <img src={options.streamUrl} alt="MJPEG Stream" className={styles.video} />;
      default:
        return <source src={options.streamUrl} type="video/mp4" />;
    }
  };

  if (!options.streamUrl) {
    return (
      <div className={styles.wrapper} style={{ width, height }}>
        <p>Please configure the stream URL in the panel options.</p>
      </div>
    );
  }

  return (
    <div className={styles.wrapper} style={{ width, height }}>
      {options.streamType === 'mjpeg' ? (
        getStreamSource()
      ) : (
        <video
          ref={videoRef}
          className={styles.video}
          controls={options.showControls}
          autoPlay={options.autoPlay}
          muted={options.muted}
          style={{ maxWidth: options.maxWidth || '100%' }}
        >
          {getStreamSource()}
          Your browser does not support the video tag.
        </video>
      )}

      {options.showControls && (
        <div className={styles.controls}>
          <button className={styles.button} onClick={togglePlay}>
            {isPlaying ? 'Pause' : 'Play'}
          </button>
          <button className={styles.button} onClick={toggleFullscreen}>
            {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          </button>
        </div>
      )}
    </div>
  );
};
