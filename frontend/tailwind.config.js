/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Extracted from template analysis
        primary: {
          50: '#fcf9f8',   // Primary background
          100: '#f3ebe7',  // Secondary background
          200: '#e8d7cf',  // Border colors
          300: '#9b644b',  // Secondary text
          400: '#8b6a5b',  // Secondary text variant
          500: '#1c120d',  // Primary text
          600: '#191310',  // Primary text variant
        },
        accent: {
          DEFAULT: '#f15f1c', // Orange CTA color
          hover: '#e54d0a',   // Darker orange for hover
        },
        background: {
          DEFAULT: '#fcf9f8', // Main background
          secondary: '#f1ece9', // Card/input backgrounds
        },
        text: {
          primary: '#1c120d',   // Dark brown
          secondary: '#9b644b', // Medium brown
          placeholder: '#9b644b', // Placeholder text
        },
        border: {
          DEFAULT: '#e8d7cf',
          light: '#f1ece9',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Noto Sans"', 'sans-serif'],
      },
      fontSize: {
        'page-title': ['32px', { lineHeight: 'tight', letterSpacing: '-0.015em' }],
        'section-title': ['28px', { lineHeight: 'tight', letterSpacing: '-0.015em' }],
        'subsection': ['22px', { lineHeight: 'tight', letterSpacing: '-0.015em' }],
      },
      spacing: {
        '18': '4.5rem', // For custom spacing needs
      },
      borderRadius: {
        'xl': '0.75rem', // For inputs and cards
      },
      animation: {
        'fadeIn': 'fadeIn 0.3s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      },
      boxShadow: {
        'recipe-card': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}