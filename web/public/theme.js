// Runs before the first paint (a file, not inline: the CSP allows only same-origin scripts), so a dark-mode
// visitor never sees a white flash. The saved choice wins; otherwise the device's setting.
(function () {
  var t = null
  try { t = localStorage.getItem('theme') } catch (e) {}
  if (t !== 'light' && t !== 'dark') t = window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  document.documentElement.classList.toggle('dark', t === 'dark')
})()
