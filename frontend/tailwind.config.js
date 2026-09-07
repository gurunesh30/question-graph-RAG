/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        /* Elegant-luxury semantic tokens mapped from CSS vars */
        background:  "var(--background)",
        foreground:  "var(--foreground)",
        card:        "var(--card)",
        "card-fg":   "var(--card-foreground)",
        muted:       "var(--muted)",
        "muted-fg":  "var(--muted-foreground)",
        border:      "var(--border)",
        input:       "var(--input)",
        ring:        "var(--ring)",
        primary: {
          DEFAULT: "var(--primary)",
          fg:      "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          fg:      "var(--secondary-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          fg:      "var(--accent-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          fg:      "var(--destructive-foreground)",
        },
        /* KG node type palette */
        hierarchy: "#16A34A",
        concept:   "#DB2777",
        textual:   "#A16207",
      },
      fontFamily: {
        sans:  ["var(--font-sans)", "system-ui", "sans-serif"],
        mono:  ["var(--font-mono)", "ui-monospace", "monospace"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        sm: "calc(var(--radius) - 2px)",
        md: "var(--radius)",
        lg: "calc(var(--radius) + 4px)",
        xl: "calc(var(--radius) + 8px)",
        "2xl": "calc(var(--radius) + 14px)",
      },
      boxShadow: {
        sm:  "var(--shadow-sm)",
        md:  "var(--shadow-md)",
        lg:  "var(--shadow-lg)",
        xl:  "var(--shadow-xl)",
        "2xl": "var(--shadow-2xl)",
      },
    },
  },
  plugins: [],
};
