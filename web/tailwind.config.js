/** @type {import('tailwindcss').Config} */
// Every colour is a CSS variable (index.css), so light and dark are one switch on <html class="dark">.
const v = (name) => `rgb(var(--c-${name}) / <alpha-value>)`

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // near-black ink and neutral surfaces; red is the one brand colour, used for action and emphasis
        white: v('surface'), // cards and fields: white by day, deep slate at night
        onbrand: '#FFFFFF', // text on red stays white in both themes
        ink: { DEFAULT: v('ink'), soft: v('ink-soft'), faint: v('ink-faint') },
        paper: { DEFAULT: v('surface'), tint: v('page'), warm: v('page') },
        rule: { DEFAULT: v('rule'), strong: v('rule-strong') },
        ledger: { DEFAULT: v('ledger'), soft: v('ledger-soft') },
        kumkum: { DEFAULT: v('red'), dark: v('red-dark'), deep: '#6E0614', soft: v('red-soft') },
        haldi: { DEFAULT: '#F2A900', dark: v('haldi-dark'), soft: v('haldi-soft') },
        leaf: { DEFAULT: v('leaf'), soft: v('leaf-soft') },
      },
      fontFamily: { sans: ['var(--font)', 'system-ui', 'sans-serif'] },
      borderRadius: { slip: '6px', pill: '999px' },
      boxShadow: {
        card: 'var(--shadow-card)',
        lift: 'var(--shadow-lift)',
        brand: '0 8px 20px -6px rgba(213,15,43,.45)',
      },
      maxWidth: { site: '1200px', form: '720px' },
      // page fade is opacity only: an animated transform would trap the phone's fixed action bar inside the page
      keyframes: { rise: { from: { opacity: '0', transform: 'translateY(6px)' }, to: { opacity: '1', transform: 'none' } }, fade: { from: { opacity: '0' }, to: { opacity: '1' } } },
      animation: { rise: 'rise .25s ease-out backwards', fade: 'fade .2s ease-out backwards' },
    },
  },
  plugins: [],
}
