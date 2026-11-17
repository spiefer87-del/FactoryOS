document.addEventListener('DOMContentLoaded', () => {
 const table = document.getElementById('article-defects-table');
 const select = document.getElementById('defect-catalog-sort');
 if (!table || !select) return;
 // Reuse the existing table's sorting, search and pagination state.
 select.addEventListener('change', () => {
  const [column, direction] = select.value.split(':');
  const header = table.querySelectorAll('thead th')[Number(column)];
  if (!header) return;
  const selectedClass = direction === 'desc' ? 'sorted-desc' : 'sorted-asc';
  if (!header.classList.contains(selectedClass)) header.click();
  if (!header.classList.contains(selectedClass)) header.click();
 });
});
