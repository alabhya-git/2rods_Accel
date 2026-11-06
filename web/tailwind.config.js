/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: '#1B1F3B', soft: '#4A4F6E', faint: '#8A8FA8' },
        paper: { DEFAULT: '#FFFFFF', tint: '#F6F8FC' },
        rule: { DEFAULT: '#D5DEEE', strong: '#AFC0DE' },
        ledger: { DEFAULT: '#2B4C8C', soft: '#E8EEF8' },
        kumkum: { DEFAULT: '#C8102E', dark: '#9E0C24', soft: '#FBE9EC' },
        haldi: { DEFAULT: '#F2A900', dark: '#B07B00', soft: '#FFF4D6' },
        leaf: { DEFAULT: '#1E7B4F', soft: '#E3F3EA' },
      },
      fontFamily: { sans: ['var(--font)', 'system-ui', 'sans-serif'] },
      borderRadius: { slip: '6px', pill: '999px' },
    },
  },
  plugins: [],
}
