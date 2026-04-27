import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18212f",
        panel: "#f7f8fa",
        line: "#d9dee8",
        signal: "#0f766e",
        alert: "#b42318",
        caution: "#b7791f"
      }
    }
  },
  plugins: []
};

export default config;

