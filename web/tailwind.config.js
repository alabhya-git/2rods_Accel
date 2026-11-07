/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // near-black ink and neutral surfaces; red is the one brand colour, used for action and emphasis
        ink: { DEFAULT: '#15171F', soft: '#4B5162', faint: '#868B9B' },
        paper: { DEFAULT: '#FFFFFF', tint: '#F5F6F8', warm: '#FBF8F7' },
        rule: { DEFAULT: '#E3E6EC', strong: '#C7CCD6' },
        ledger: { DEFAULT: '#23468A', soft: '#EBF0F9' },
        kumkum: { DEFAULT: '#D50F2B', dark: '#A80C22', deep: '#6E0614', soft: '#FDEDEF' },
        haldi: { DEFAULT: '#F2A900', dark: '#9A6B00', soft: '#FFF5DB' },
        leaf: { DEFAULT: '#18794B', soft: '#E4F4EB' },
      },
      fontFamily: { sans: ['var(--font)', 'system-ui', 'sans-serif'] },
      borderRadius: { slip: '6px', pill: '999px' },
      boxShadow: {
        card: '0 1px 2px rgba(16,24,40,.04), 0 2px 10px rgba(16,24,40,.05)',
        lift: '0 12px 32px -8px rgba(16,24,40,.18), 0 2px 6px rgba(16,24,40,.06)',
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
