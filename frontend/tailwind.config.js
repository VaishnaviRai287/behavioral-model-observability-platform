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
        // White-and-pink editorial theme. Names are kept stable (only the
        // hex values flipped) so every existing bg-*/text-* class in the app
        // repaints correctly without a class-name rewrite:
        //   ink   — page background (was near-black, now white)
        //   paper — primary text / dark surfaces (was cream, now near-black)
        //   panel — card/section background (was near-black, now pink)
        //   line  — hairline borders (stays near-black, reads crisp on white/pink)
        //   mute  — secondary text (darkened so it stays legible on light bg)
        //   accent— CTAs / active states (was orange, now a deeper rose-pink)
        ink: "#FFFFFF",
        paper: "#1A1613",
        panel: "#F2B9C8",
        line: "#211C19",
        mute: "#8A6A70",
        accent: "#D6547A",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
        serif: ["var(--font-serif)", "serif"],
      },
    },
  },
  plugins: [],
};
