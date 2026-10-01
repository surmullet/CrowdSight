/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        abyssal: 'var(--color-bg-abyssal)',
        deck: 'var(--color-bg-deck)',
        contour: 'var(--color-border-contour)',
        'signal-gold': 'var(--color-accent-gold)',
        'text-primary': 'var(--color-text-primary)',
        'text-muted': 'var(--color-text-muted)',
        zone: {
          blue: '#56B4E9',
          green: '#009E73',
          vermilion: '#D55E00',
          purple: '#CC79A7',
        },
        quality: {
          valid: '#2EC4B6',
          partial: '#E7A93B',
          unknown: '#7E8B9B',
          stale: '#A25B7B',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Be Vietnam Pro', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
