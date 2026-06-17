/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/hooks/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: "#0B0F19",
        darkCard: "#161B2E",
        darkBorder: "#1F293D",
        darkHover: "#252D44",
        brandPrimary: "#0D9488", // Teal 600
        brandSecondary: "#06B6D4", // Cyan 500
        brandGlow: "rgba(13, 148, 136, 0.15)",
      },
    },
  },
  plugins: [],
};
