/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: '#FDFCF8',
        canvas: '#E7E5E4',
        ink: '#1C1917',
        sepia: '#78350F',
        accent: '#9A3412',
      },
      fontFamily: {
        'serif-custom': ['"Cormorant Garamond"', 'serif'],
        'sans-custom': ['Inter', 'sans-serif'],
        'mono-custom': ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'enter': 'fadeIn 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(15px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backdropBlur: {
        'glass': '20px',
        'input': '24px',
      },
    },
  },
  plugins: [],
}
