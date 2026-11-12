// Desktop collapse preference and accessible mobile drawer.
const adminNarrow = matchMedia('(max-width: 700px)');
function initAdminShell() {
  document.getElementById('adminName').textContent = appState.currentUser.display_name;
  const initials = getInitials(appState.currentUser.display_name);
  if (document.getElementById('adminAvatar')) document.getElementById('adminAvatar').textContent = initials;
  if (document.getElementById('adminTopAvatar')) document.getElementById('adminTopAvatar').textContent = initials;
  let collapsed = false;
  try { collapsed = localStorage.getItem('admin_sidebar_collapsed') === 'true'; } catch (_) {}
  document.body.classList.toggle('admin-collapsed', collapsed);
  closeAdminMenu();
  syncAdminToggle();
}
function syncAdminToggle() {
  const toggle = document.getElementById('adminSidebarToggle');
  if (!toggle) return;
  const expanded = adminNarrow.matches ? document.body.classList.contains('admin-menu-open') : !document.body.classList.contains('admin-collapsed');
  toggle.setAttribute('aria-expanded', String(expanded));
  toggle.setAttribute('aria-label', adminNarrow.matches ? (expanded ? 'Tutup menu admin' : 'Buka menu admin') : (expanded ? 'Ciutkan sidebar' : 'Perluas sidebar'));
  const sidebar = document.getElementById('adminSidebar');
  if (sidebar) sidebar.inert = adminNarrow.matches && !expanded;
}
function closeAdminMenu(restoreFocus = false) {
  document.body.classList.remove('admin-menu-open');
  document.getElementById('adminMenuShade')?.classList.add('hidden');
  syncAdminToggle();
  if (restoreFocus) document.getElementById('adminSidebarToggle')?.focus();
}
function toggleAdminSidebar() {
  if (adminNarrow.matches) {
    const open = document.body.classList.toggle('admin-menu-open');
    document.getElementById('adminMenuShade').classList.toggle('hidden', !open);
  } else {
    const collapsed = document.body.classList.toggle('admin-collapsed');
    try { localStorage.setItem('admin_sidebar_collapsed', String(collapsed)); } catch (_) {}
  }
  syncAdminToggle();
}
adminNarrow.addEventListener('change', closeAdminMenu);
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && document.body.classList.contains('admin-menu-open')) {
    closeAdminMenu(); document.getElementById('adminSidebarToggle')?.focus();
  }
  if (event.key === 'Tab' && adminNarrow.matches && document.body.classList.contains('admin-menu-open')) {
    const items = [...document.querySelectorAll('#adminSidebar a, #adminSidebar button, #adminSidebarToggle')].filter(el => el.getClientRects().length);
    if (event.shiftKey && event.target === items[0]) { event.preventDefault(); items.at(-1)?.focus(); }
    else if (!event.shiftKey && event.target === items.at(-1)) { event.preventDefault(); items[0]?.focus(); }
  }
});
