import type { Config } from "tailwindcss";
import slate from "tailwindcss/colors";
import amber from "tailwindcss/colors";
import red from "tailwindcss/colors";

// Design tokens from spec §4.1.
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        midnight: "#101C2C",
        teal: {
          DEFAULT: "#176B63",
          dark: "#0F4F49",
        },
        mint: "#BDE9D9",
        ivory: "#F7F6F1",
        slate: slate.slate,
        amber: amber.amber,
        red: red.red,
        border: "#E2E8F0",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      fontVariantNumeric: {
        tabular: "tabular-nums",
      },
      borderRadius: {
        lg: "12px",
        xl: "16px",
        "2xl": "20px",
      },
    },
  },
  plugins: [],
};

export default config;