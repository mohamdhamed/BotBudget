/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./dashboard/templates/**/*.html",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Cairo', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
