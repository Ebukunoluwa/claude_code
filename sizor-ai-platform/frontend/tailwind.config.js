/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        nhs: {
          blue: "#003087",
          "blue-light": "#0072CE",
          red: "#DC2626",
          amber: "#D97706",
          green: "#16A34A",
          grey: "#768692",
          bg: "#f1f5f9",
        },
        sidebar: {
          bg: "#0f1729",
          hover: "#1e2a45",
          active: "#1e3a6e",
          border: "#1e2a45",
          text: "#94a3b8",
          "text-active": "#ffffff",
        },
      },
      fontFamily: {
        sans: ["'Inter'", "'Arial'", "sans-serif"],
      },
      backgroundImage: {
        "gradient-blue": "linear-gradient(135deg, #003087 0%, #0072CE 100%)",
        "gradient-indigo": "linear-gradient(135deg, #4338ca 0%, #6366f1 100%)",
        "gradient-red": "linear-gradient(135deg, #be123c 0%, #f43f5e 100%)",
        "gradient-amber": "linear-gradient(135deg, #b45309 0%, #f59e0b 100%)",
        "gradient-rose": "linear-gradient(135deg, #9f1239 0%, #e11d48 100%)",
        "gradient-green": "linear-gradient(135deg, #166534 0%, #22c55e 100%)",
      },
    },
  },
  plugins: [],
};
