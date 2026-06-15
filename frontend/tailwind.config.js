/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#070b14",
          sunken: "#050811",
        },
        panel: {
          DEFAULT: "#0d1422",
          raised: "#121b2d",
          hover: "#18233a",
        },
        accent: {
          DEFAULT: "#4f9cff",
          strong: "#2f7fff",
        },
        teal: {
          DEFAULT: "#2dd4bf",
        },
        line: {
          DEFAULT: "#1c2740",
          strong: "#2a3a5c",
        },
        ink: {
          DEFAULT: "#e8eef9",
          muted: "#9fb0cc",
          faint: "#5e6f8f",
        },
        state: {
          info: "#4f9cff",
          warning: "#d8b25a",
          critical: "#f4607a",
          ok: "#2dd4bf",
        },
      },
      borderRadius: {
        card: "14px",
        pill: "999px",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.02), 0 12px 40px -16px rgba(0,0,0,0.6)",
      },
    },
  },
  plugins: [],
};
