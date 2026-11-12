// Searchable comboboxes preserve the original select values and change events.
function initAdminComboboxes() {
  document.querySelectorAll('#viewAdmin select, #prepareForm select, #historyFilter').forEach(select => {
    if (select.dataset.combobox) return;
    select.dataset.combobox = 'true';
    const wrapper = document.createElement('div'); wrapper.className = 'admin-combobox';
    wrapper.dataset.select = select.id;
    const input = document.createElement('input'); input.type = 'text'; input.autocomplete = 'off';
    input.id = select.id + '-combo'; input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list'); input.setAttribute('aria-expanded', 'false');
    const list = document.createElement('div'); list.id = input.id + '-list'; list.className = 'combo-list hidden'; list.setAttribute('role', 'listbox');
    input.setAttribute('aria-controls', list.id);
    document.querySelectorAll(`label[for="${select.id}"]`).forEach(label => {
      label.htmlFor = input.id;
      input.setAttribute('aria-label', label.textContent);
    });
    select.before(wrapper); wrapper.append(input, list); select.classList.add('combo-source');
    select.setAttribute('aria-hidden', 'true'); select.tabIndex = -1;
    let active = -1;
    const close = () => { list.classList.add('hidden'); input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); sync(); };
    const sync = () => { input.disabled = select.disabled; if (input.getAttribute('aria-expanded') !== 'true') input.value = select.selectedOptions[0]?.textContent || ''; };
    const render = (filter = '') => {
      list.replaceChildren(); active = -1;
      [...select.options].filter(option => !option.disabled && option.text.toLowerCase().includes(filter.toLowerCase())).forEach(option => {
        const item = document.createElement('div'); item.id = list.id + '-' + list.children.length;
        item.setAttribute('role', 'option'); item.setAttribute('aria-selected', String(option.selected)); item.textContent = option.text;
        item.addEventListener('pointerdown', event => { event.preventDefault(); select.value = option.value; select.dispatchEvent(new Event('change', { bubbles: true })); close(); input.focus(); });
        list.append(item);
      });
      if (!list.children.length) { const empty = document.createElement('p'); empty.textContent = 'Tidak ada pilihan'; list.append(empty); }
      list.classList.remove('hidden'); input.setAttribute('aria-expanded', 'true');
    };
    input.addEventListener('focus', () => { input.select(); render(); });
    input.addEventListener('click', () => render());
    input.addEventListener('input', () => render(input.value));
    input.addEventListener('blur', close);
    input.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); close(); return; }
      if (!['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) return;
      event.preventDefault();
      if (input.getAttribute('aria-expanded') !== 'true') render();
      const items = [...list.querySelectorAll('[role="option"]')];
      if (!items.length) return;
      if (event.key === 'Enter') { if (active >= 0) items[active].dispatchEvent(new PointerEvent('pointerdown')); return; }
      active = (active + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items.forEach((item, index) => item.classList.toggle('is-highlighted', index === active));
      input.setAttribute('aria-activedescendant', items[active].id); items[active].scrollIntoView({ block: 'nearest' });
    });
    select._syncCombobox = sync;
    select.addEventListener('change', sync);
    const observer = new MutationObserver(() => { if (!select.isConnected) { observer.disconnect(); return; } select._syncCombobox?.(); });
    observer.observe(select, { childList: true, subtree: true, attributes: true });
    sync();
  });
}
