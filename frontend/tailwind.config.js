/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          950: '#050811',
          900: '#070B14',
          850: '#0B0F19',
          800: '#111827',
          700: '#1E293B',
          600: '#334155',
        },
        jarvis: {
          cyan: '#00F0FF',
          blue: '#0070F3',
          glow: 'rgba(0, 240, 255, 0.4)',
          amber: '#F59E0B',
          red: '#EF4444',
          emerald: '#10B981',
        }
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 12s linear infinite',
        'spin-reverse': 'spin-reverse 8s linear infinite',
        'ripple': 'ripple 1.5s ease-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '0.9', transform: 'scale(1)' },
          '50%': { opacity: '0.4', transform: 'scale(1.05)' },
        },
        'spin-reverse': {
          'from': { transform: 'rotate(360deg)' },
          'to': { transform: 'rotate(0deg)' },
        },
        'ripple': {
          '0%': { transform: 'scale(0.8)', opacity: '1' },
          '100%': { transform: 'scale(2.2)', opacity: '0' },
        }
      },
      boxShadow: {
        'arc': '0 0 25px rgba(0, 240, 255, 0.45), inset 0 0 15px rgba(0, 240, 255, 0.3)',
        'cyan-glow': '0 0 15px rgba(0, 240, 255, 0.3)',
        'amber-glow': '0 0 15px rgba(245, 158, 11, 0.4)',
        'red-glow': '0 0 20px rgba(239, 68, 68, 0.5)',
      }
    },
  },
  plugins: [],
}
