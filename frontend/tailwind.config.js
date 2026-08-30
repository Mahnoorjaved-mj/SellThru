/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        app: 'var(--color-bg-muted)',
        bg: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        'surface-hover': 'var(--color-surface-hover)',
        line: 'var(--color-border)',
        'line-strong': 'var(--color-border-strong)',
        primary: 'var(--color-text)',
        secondary: 'var(--color-text-secondary)',
        tertiary: 'var(--color-text-tertiary)',
        accent: 'var(--color-accent)',
        'accent-hover': 'var(--color-accent-hover)',
        'accent-soft': 'var(--color-accent-soft)',
        up: 'var(--color-positive)',
        'up-soft': 'var(--color-positive-soft)',
        down: 'var(--color-negative)',
        'down-soft': 'var(--color-negative-soft)',
        warn: 'var(--color-warning)',
        'warn-soft': 'var(--color-warning-soft)',
        overlay: 'var(--color-overlay)',
      },
      borderRadius: {
        DEFAULT: 'var(--radius-control)',
        control: 'var(--radius-control)',
        panel: 'var(--radius-panel)',
        lg: 'var(--radius-panel)',
      },
      boxShadow: {
        elevated: 'var(--shadow-elevated)',
      },
      fontFamily: {
        body: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        eyebrow: ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.06em' }], // 11px
        cell: ['0.75rem', { lineHeight: '1.1rem' }], // 12px
        body: ['0.8125rem', { lineHeight: '1.25rem' }], // 13px
        default: ['0.875rem', { lineHeight: '1.35rem' }], // 14px
        section: ['1rem', { lineHeight: '1.4rem' }], // 16px
        page: ['1.25rem', { lineHeight: '1.6rem' }], // 20px
        kpi: ['1.75rem', { lineHeight: '2.1rem' }], // 28px
      },
      spacing: {
        4.5: '1.125rem',
      },
      transitionDuration: {
        120: '120ms',
      },
    },
  },
  plugins: [],
}
