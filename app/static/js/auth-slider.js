// Carrusel de la pantalla de acceso. No utiliza bibliotecas ni servicios externos.
(() => {
  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = button.parentElement.querySelector('input');
      if (!input) return;
      const reveal = input.type === 'password';
      input.type = reveal ? 'text' : 'password';
      button.textContent = reveal ? 'Ocultar' : 'Mostrar';
      button.setAttribute('aria-pressed', String(reveal));
      button.setAttribute('aria-label', reveal ? 'Ocultar contraseña' : 'Mostrar contraseña');
    });
  });
  const slider = document.querySelector('[data-auth-slider]');
  if (!slider) return;
  const slides = [...slider.querySelectorAll('[data-auth-slide]')];
  const dots = [...slider.querySelectorAll('[data-auth-dot]')];
  const prev = slider.querySelector('[data-auth-prev]');
  const next = slider.querySelector('[data-auth-next]');
  if (slides.length < 2) return;
  let current = 0;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const go = (index) => {
    current = (index + slides.length) % slides.length;
    slides.forEach((slide, i) => {
      const active = i === current;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', String(!active));
    });
    dots.forEach((dot, i) => {
      dot.classList.toggle('is-active', i === current);
      if (i === current) dot.setAttribute('aria-current', 'true');
      else dot.removeAttribute('aria-current');
    });
  };
  let timer;
  const stop = () => { if (timer) window.clearInterval(timer); timer = undefined; };
  const start = () => {
    stop();
    if (reducedMotion.matches || document.hidden) return;
    timer = window.setInterval(() => go(current + 1), 6500);
  };
  prev?.addEventListener('click', () => { go(current - 1); start(); });
  next?.addEventListener('click', () => { go(current + 1); start(); });
  dots.forEach((dot, i) => dot.addEventListener('click', () => { go(i); start(); }));
  slider.addEventListener('mouseenter', stop);
  slider.addEventListener('mouseleave', start);
  slider.addEventListener('focusin', stop);
  slider.addEventListener('focusout', (event) => { if (!slider.contains(event.relatedTarget)) start(); });
  document.addEventListener('visibilitychange', start);
  reducedMotion.addEventListener?.('change', start);
  go(0);
  start();
})();
