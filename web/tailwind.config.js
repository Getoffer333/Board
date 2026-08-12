/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,js}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#4f46e5',
          soft: '#eef2ff'
        }
      }
    }
  },
  plugins: []
}
