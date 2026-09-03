/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          950: '#080b14',
          900: '#0d1220',
          850: '#121a2c',
          800: '#18223a',
          700: '#22304f',
          600: '#31425f',
        },
        accent: {
          DEFAULT: '#38bdf8',
          soft: '#7dd3fc',
        },
      },
      fontFamily: {
        sans: ['"Inter var"', 'Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};
