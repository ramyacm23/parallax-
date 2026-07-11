// ── PARALLAX main.js ── HackForge + Parallax fusion

// Scroll progress bar
const progressBar = document.getElementById('progress-bar');
if (progressBar) {
  window.addEventListener('scroll', () => {
    const scrolled = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
    progressBar.style.width = scrolled + '%';
  }, { passive: true });
}

// Cursor glow effect
const cursorGlow = document.getElementById('cursor-glow');
if (cursorGlow) {
  document.addEventListener('mousemove', (e) => {
    cursorGlow.style.left = e.clientX + 'px';
    cursorGlow.style.top = e.clientY + 'px';
  }, { passive: true });
}

// Nav scroll state
const nav = document.getElementById('nav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 40);
  }, { passive: true });
}

// Scroll reveal via IntersectionObserver
(function () {
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('in');
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));
})();

// Parallax scroll on hero geometry (home only)
const geoWrap = document.getElementById('geoWrap');
if (geoWrap) {
  window.addEventListener('scroll', () => {
    geoWrap.style.transform = 'translateY(' + (window.scrollY * 0.16) + 'px)';
  }, { passive: true });
}
