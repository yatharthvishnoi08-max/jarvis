import React from 'react';
import { OrbState } from '../types';

interface JarvisOrbProps {
  state: OrbState;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onClick?: () => void;
}

export const JarvisOrb: React.FC<JarvisOrbProps> = ({
  state,
  size = 'md',
  className = '',
  onClick
}) => {
  const sizeMap = {
    sm: 'w-16 h-16',
    md: 'w-28 h-28 sm:w-36 sm:h-36',
    lg: 'w-44 h-44 sm:w-56 sm:h-56',
  };

  const getTheme = () => {
    switch (state) {
      case 'listening':
        return {
          primary: '#10B981', // emerald
          secondary: '#34D399',
          glow: 'rgba(16, 185, 129, 0.45)',
          spinClass: 'animate-spin-slow',
          pulseClass: 'animate-pulse-glow',
        };
      case 'thinking':
        return {
          primary: '#00F0FF',
          secondary: '#0070F3',
          glow: 'rgba(0, 240, 255, 0.6)',
          spinClass: 'animate-spin',
          pulseClass: 'animate-pulse',
        };
      case 'acting':
        return {
          primary: '#38BDF8',
          secondary: '#818CF8',
          glow: 'rgba(56, 189, 248, 0.55)',
          spinClass: 'animate-spin-reverse',
          pulseClass: 'animate-pulse-glow',
        };
      case 'speaking':
        return {
          primary: '#00F0FF',
          secondary: '#60A5FA',
          glow: 'rgba(0, 240, 255, 0.7)',
          spinClass: 'animate-spin-slow',
          pulseClass: 'animate-bounce',
        };
      case 'disconnected':
        return {
          primary: '#F59E0B', // amber
          secondary: '#78350F',
          glow: 'rgba(245, 158, 11, 0.3)',
          spinClass: '',
          pulseClass: '',
        };
      case 'error':
        return {
          primary: '#EF4444', // red
          secondary: '#7F1D1D',
          glow: 'rgba(239, 68, 68, 0.6)',
          spinClass: '',
          pulseClass: 'animate-ping',
        };
      case 'idle':
      default:
        return {
          primary: '#00F0FF',
          secondary: '#0070F3',
          glow: 'rgba(0, 240, 255, 0.35)',
          spinClass: 'animate-spin-slow',
          pulseClass: 'animate-pulse-glow',
        };
    }
  };

  const theme = getTheme();

  return (
    <div
      onClick={onClick}
      className={`relative flex items-center justify-center cursor-pointer select-none transition-all duration-300 ${sizeMap[size]} ${className}`}
      style={{ filter: `drop-shadow(0 0 16px ${theme.glow})` }}
      role="button"
      tabIndex={0}
      aria-label={`JARVIS Status: ${state}`}
    >
      {/* Outer Halo Ring */}
      <div
        className={`absolute inset-0 rounded-full border border-dashed transition-all duration-500 ${theme.spinClass}`}
        style={{ borderColor: theme.primary, opacity: 0.6 }}
      />

      {/* Counter-Rotating Middle Energy Ring */}
      <div
        className="absolute inset-2 rounded-full border border-dotted transition-all duration-500 animate-spin-reverse"
        style={{ borderColor: theme.secondary, opacity: 0.5 }}
      />

      {/* Inner Segment Ring */}
      <svg className="absolute inset-4 w-full h-full transform -rotate-45" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="40"
          fill="none"
          stroke={theme.primary}
          strokeWidth="2.5"
          strokeDasharray="25 15"
          opacity="0.8"
        />
      </svg>

      {/* Concentric Energy Core */}
      <div
        className={`relative flex items-center justify-center rounded-full transition-all duration-300 ${theme.pulseClass}`}
        style={{
          width: '42%',
          height: '42%',
          background: `radial-gradient(circle, #FFFFFF 0%, ${theme.primary} 50%, rgba(5,8,17,0.9) 100%)`,
          boxShadow: `0 0 25px ${theme.primary}, inset 0 0 10px #FFFFFF`,
        }}
      >
        {/* Core Hotspot */}
        <div className="w-2.5 h-2.5 bg-white rounded-full shadow-lg" />
      </div>

      {/* Acoustic Wave Ripple (when speaking/listening) */}
      {(state === 'speaking' || state === 'listening') && (
        <div
          className="absolute inset-0 rounded-full border animate-ripple pointer-events-none"
          style={{ borderColor: theme.primary }}
        />
      )}
    </div>
  );
};
