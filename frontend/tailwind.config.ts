import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "#e0e0e0",
        input: "#f0f0f0",
        ring: "#0071e3",
        background: "#f5f5f7",
        foreground: "#1d1d1f",
        card: "#ffffff",
        "card-foreground": "#1d1d1f",
        primary: {
          DEFAULT: "#0066cc",
          foreground: "#ffffff",
        },
        muted: {
          DEFAULT: "#fafafc",
          foreground: "#7a7a7a",
        },
        accent: {
          DEFAULT: "#0071e3",
          foreground: "#ffffff",
        },
        success: "#00b259",
        warning: "#f5a623",
        danger: "#ff3b30",
        ink: {
          DEFAULT: "#1d1d1f",
          muted: "#7a7a7a",
        },
        canvas: {
          DEFAULT: "#ffffff",
          parchment: "#f5f5f7",
        }
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
        "3xl": "1.5rem",
      },
      letterSpacing: {
        "apple-tight": "-0.01em",
        "apple-loose": "0.01em",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
