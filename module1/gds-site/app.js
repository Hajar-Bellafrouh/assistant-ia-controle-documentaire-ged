// ============================================
// CONFIG — liens vers les deux modules IA, dossiers
// voisins de gds-site à la racine du projet.
// ============================================
const ASSISTANT_URL = "../webapp-assistant/index.html";
const CONTROLE_URL = "../../PFA-Module2-ControleDocumentaire/controle-documentaire/index.html";

document.querySelectorAll('[id^="assistant-link"]')
  .forEach(el => {
    if (!el) return;
    el.href = ASSISTANT_URL;
    el.removeAttribute('target');
    el.removeAttribute('rel');
  });

document.querySelectorAll('[id^="controle-link"]')
  .forEach(el => {
    if (!el) return;
    el.href = CONTROLE_URL;
    el.removeAttribute('target');
    el.removeAttribute('rel');
  });

// Mobile nav toggle
const toggle = document.querySelector('.menu-toggle');
const links = document.querySelector('nav.links');
if (toggle && links) {
  toggle.addEventListener('click', () => {
    const open = links.style.display === 'flex';
    links.style.display = open ? 'none' : 'flex';
    links.style.flexDirection = 'column';
    links.style.position = 'absolute';
    links.style.top = '68px';
    links.style.left = '0';
    links.style.right = '0';
    links.style.background = 'var(--surface)';
    links.style.padding = '20px 32px';
    links.style.borderBottom = '1px solid var(--line)';
    links.style.gap = '16px';
  });
}
