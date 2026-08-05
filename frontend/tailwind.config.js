/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: { ink: "#060816", navy: "#0b1230" },
      boxShadow: { glow: "0 0 40px rgba(91, 140, 255, .22)" },
    },
  },
  plugins: [],
};
