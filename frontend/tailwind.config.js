/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        gold: {
          50:  "#fdf8ee",
          100: "#f9edcc",
          200: "#f2d98a",
          300: "#e8c04a",
          400: "#d4a832",
          500: "#c9a96e",  // primary brand gold
          600: "#a8863d",
          700: "#7d6128",
          800: "#5a4519",
          900: "#3a2c0e",
        },
        stone: {
          50:  "#f8f7f4",
          100: "#eeece6",
          200: "#ddd9ce",
          300: "#c5bfb0",
          400: "#a89e8c",
          500: "#8c8070",
          600: "#6e6356",
          700: "#534a3f",
          800: "#38322a",
          900: "#1e1a15",
        },
      },
      fontFamily: {
        serif: ["var(--font-cormorant)", "Georgia", "serif"],
        sans:  ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      fontSize: {
        "display": ["clamp(2.5rem, 5vw, 4rem)", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
        "heading":  ["clamp(1.75rem, 3vw, 2.5rem)", { lineHeight: "1.2" }],
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
