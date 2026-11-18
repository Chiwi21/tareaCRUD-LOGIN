(function () {
  'use strict';
  const input = document.querySelector('#tr-glossary-search');
  if (!input) return;
  const norm = (v) => v.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const groups = [...document.querySelectorAll('[data-glossary-group]')];
  input.addEventListener('input', () => {
    const query = norm(input.value.trim());
    groups.forEach(group => {
      let visible = 0;
      group.querySelectorAll('[data-glossary-entry]').forEach(entry => {
        const matches = norm(entry.textContent).includes(query);
        entry.hidden = !matches;
        if (matches) visible++;
      });
      group.hidden = !visible;
    });
  });
})();
