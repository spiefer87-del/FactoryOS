document.addEventListener('DOMContentLoaded', () => {
 const form = document.querySelector('[data-project-create]');
 if (!form) return;
 const configs = JSON.parse(document.getElementById('project-type-config').textContent);
 const kind = form.querySelector('[data-project-kind]');
 const reference = form.querySelector('[data-project-reference]');
 const hint = form.querySelector('[data-project-hint]');
 const update = (changedKind = false) => {
  const config = configs[kind.value];
  hint.textContent = config ? config.hint : 'Der Projektgrund bestimmt, welche Bereiche später angezeigt werden.';
  if (changedKind && config) {
   if (config.sampling_required && reference.querySelector('option[value="sampling"]')) reference.value = 'sampling';
   else if (config.tool_required && reference.value === 'none') reference.value = 'tool';
  }
  form.querySelectorAll('[data-reference-panel]').forEach(panel => {
   const active = panel.dataset.referencePanel === reference.value;
   panel.hidden = !active;
   const select = panel.querySelector('select');
   select.disabled = !active;
   select.required = active;
  });
 };
 kind.addEventListener('change', () => update(true));
 reference.addEventListener('change', () => update());
 update();
});
