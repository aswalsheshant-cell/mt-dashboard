import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        teal: {
          50:  '#E6F7F5',
          100: '#C2EBE7',
          200: '#9ADDD7',
          300: '#6ECEC5',
          400: '#4CC1B5',
          500: '#00A896',
          600: '#00897B',
          700: '#00695C',
          800: '#004D40',
          900: '#003330',
        },
      },
      fontFamily: {
        sans: ["'Inter'", "'Segoe UI'", 'system-ui', 'sans-serif'],
        mono: ["'JetBrains Mono'", "'Fira Code'", 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config;
