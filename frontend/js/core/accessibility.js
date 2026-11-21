// Shared focus targets for SPA routes, skip links and in-page navigation.
function focusPageContent() {
  const main = document.querySelector('main');
  if (!main) return;
  if (!document.getElementById('mainContent')) {
    const content = main.querySelector('.admin-content') || main;
    if (!content.id) content.id = 'mainContent';
    // The exam main keeps its existing ID, which is used by telemetry.
    document.querySelector('.skip-link').href = '#' + content.id;
  } else document.querySelector('.skip-link').href = '#mainContent';
  main.tabIndex = -1;
  main.focus({ preventScroll: true });
}

function focusPageAnchor(hash) {
  let id;
  try { id = decodeURIComponent(hash.slice(1)); } catch (_) { return; }
  const target = document.getElementById(id);
  if (!target) return;
  if (!target.matches('a[href],button,input,select,textarea,[tabindex]')) target.tabIndex = -1;
  target.focus({ preventScroll: true });
  target.scrollIntoView({ block: 'start' });
}
