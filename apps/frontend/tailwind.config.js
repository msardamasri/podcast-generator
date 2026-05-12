/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0a",
        surface: "#141414",
        border: "#262626",
        muted: "#737373",
        text: "#e5e5e5",
        accent: "#3b82f6",
      },
    },
  },
  plugins: [],
};