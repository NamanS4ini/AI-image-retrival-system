function setupImageSearch(onSearch, restoredEntry) {
  const details = document.getElementById('image-search');
  const form = document.getElementById('image-search-form');
  const fileInput = document.getElementById('reference-image');
  const preview = document.getElementById('reference-image-preview');
  const restoreNotice = document.getElementById('reference-image-restore');
  const keywords = document.getElementById('reference-keywords');
  const submit = form.querySelector('button[type="submit"]');
  let previewUrl;

  if (restoredEntry?.type.endsWith('-image')) {
    details.open = true;
    restoreNotice.textContent = `Choose “${restoredEntry.query}” again to repeat this search.`;
    restoreNotice.hidden = false;
    if (keywords) keywords.value = restoredEntry.keywords || '';
  }

  fileInput.addEventListener('change', () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    preview.removeAttribute('src');
    preview.hidden = true;
    const file = fileInput.files[0];
    fileInput.setCustomValidity(file?.size > 10 * 1024 * 1024 ? 'Choose an image up to 10 MB.' : '');
    if (!file || !fileInput.reportValidity()) return;

    restoreNotice.hidden = true;
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
  });

  preview.addEventListener('error', () => { preview.hidden = true; });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (submit.disabled) return;
    submit.disabled = true;
    submit.textContent = 'Searching…';
    try {
      await onSearch(new FormData(form), form.getAttribute('action'));
    } finally {
      submit.disabled = false;
      submit.textContent = 'Find similar images';
    }
  });
}
