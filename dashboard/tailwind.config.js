/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ops: {
          bg: "#0b1220",
          panel: "#0f1a2e",
          rail: "#131f37",
          border: "#1e2a44",
          accent: "#22d3ee",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};