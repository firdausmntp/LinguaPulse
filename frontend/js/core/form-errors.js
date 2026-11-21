// Keep error text next to the field and include it in the field's accessible description.
function clearFieldError(field) {
  const target = document.getElementById(field.id + '-combo') || field;
  const id = target.id + '-error';
  const message = document.getElementById(id);
  if (!message) return;
  message.remove();
  target.removeAttribute('aria-invalid');
  const description = (target.getAttribute('aria-describedby') || '').split(/\s+/).filter(value => value && value !== id);
  if (description.length) target.setAttribute('aria-describedby', description.join(' '));
  else target.removeAttribute('aria-describedby');
}

function setFieldError(field, text, focus = true) {
  clearFieldError(field);
  const target = document.getElementById(field.id + '-combo') || field;
  const message = document.createElement('small');
  message.id = target.id + '-error';
  message.className = 'field-error';
  message.textContent = text;
  const anchor = target.closest('.password-field, .checkbox-label, .admin-combobox, .question-option-edit') || target;
  anchor.after(message);
  target.setAttribute('aria-invalid', 'true');
  target.setAttribute('aria-describedby', [target.getAttribute('aria-describedby'), message.id].filter(Boolean).join(' '));
  if (focus) target.focus();
  return target;
}

function showFormError(summary, message, focus = true) {
  summary.textContent = message;
  summary.classList.remove('hidden');
  if (focus) {
    summary.tabIndex = -1;
    summary.focus();
  }
}

function fieldValidationMessage(field) {
  const { validity, dataset, value } = field;
  if (validity.valueMissing || (field.required && ['text', 'textarea'].includes(field.type) && !value.trim())) {
    if (field.type === 'checkbox') return dataset.errorRequired || 'Centang persetujuan untuk melanjutkan.';
    return 'Kolom ini wajib diisi.';
  }
  if (validity.typeMismatch && field.type === 'email') return 'Masukkan alamat email seperti nama@contoh.id.';
  if (field.type === 'number' && (validity.badInput || validity.rangeUnderflow || validity.rangeOverflow || validity.stepMismatch)) {
    return `Masukkan bilangan bulat dari ${field.min} sampai ${field.max}.`;
  }
  if (validity.patternMismatch) return dataset.errorPattern || 'Periksa format yang diminta untuk kolom ini.';
  if (validity.tooShort) return `Masukkan minimal ${field.minLength} karakter.`;
  if (validity.tooLong) return `Gunakan maksimal ${field.maxLength} karakter.`;
  return validity.valid ? '' : field.validationMessage;
}

function enableFormErrors(form, extra = () => ({})) {
  form.noValidate = true;
  const clear = event => {
    if (event.target.id && event.target.validity) clearFieldError(event.target);
  };
  form.addEventListener('input', clear);
  form.addEventListener('change', clear);
  form.addEventListener('reset', () => {
    for (const field of form.elements) if (field.id) clearFieldError(field);
  });
  form.addEventListener('submit', event => {
    let first;
    const custom = extra(form);
    for (const field of form.elements) {
      if (!field.id || !field.willValidate) continue;
      clearFieldError(field);
      const message = fieldValidationMessage(field) || custom[field.id];
      if (!message) continue;
      const target = setFieldError(field, message, false);
      first ||= target;
    }
    if (first) {
      event.preventDefault();
      event.stopImmediatePropagation();
      first.focus();
    }
  }, true);
}
