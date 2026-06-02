const btn = document.getElementById('themeBtn');
function applyAccessibleState() {
  if (localStorage.getItem('accessible') === '1') {
    document.body.classList.add('accessible');
    if (btn) btn.textContent = 'Обычная версия';
  } else if (btn) {
    btn.textContent = 'Версия для слабовидящих';
  }
}
applyAccessibleState();
btn?.addEventListener('click', () => {
  document.body.classList.toggle('accessible');
  localStorage.setItem('accessible', document.body.classList.contains('accessible') ? '1' : '0');
  applyAccessibleState();
});
