/** @type {import('tailwindcss').Config} */
import defaultTheme from 'tailwindcss/defaultTheme'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Couleurs de décision SSVC (signalétique métier, ne pas modifier)
        'ssvc-act': '#dc2626',
        'ssvc-attend': '#f97316',
        'ssvc-track-star': '#eab308',
        'ssvc-track': '#22c55e',
      },
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
        mono: ['"JetBrains Mono"', ...defaultTheme.fontFamily.mono],
      },
      borderRadius: {
        // Radius des surfaces (cards, dialogs) — spec « Ardoise & Indigo »
        card: '10px',
      },
    },
  },
  plugins: [],
}
