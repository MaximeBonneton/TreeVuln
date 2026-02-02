/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // SSVC Decision colors
        'ssvc-act': '#dc2626',
        'ssvc-attend': '#f97316',
        'ssvc-track-star': '#eab308',
        'ssvc-track': '#22c55e',
      },
    },
  },
  plugins: [],
}
