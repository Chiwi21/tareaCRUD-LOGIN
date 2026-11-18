(() => {
  const toggle = document.querySelector("[data-sidebar-toggle]");
  const overlay = document.querySelector("[data-sidebar-scrim]");
  const app = document.getElementById("it-app");
  if (!toggle || !app) return;
  const close = () => { app.classList.remove("it-sidebar-open"); toggle.setAttribute("aria-expanded", "false"); };
  toggle.addEventListener("click", () => { const open = app.classList.toggle("it-sidebar-open"); toggle.setAttribute("aria-expanded", String(open)); });
  overlay?.addEventListener("click", close);
  document.addEventListener("keydown", event => { if (event.key === "Escape") close(); });
})();
