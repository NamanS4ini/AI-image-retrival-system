const searchHistory = (() => {
  const prefix = 'image-retrieval.history.';
  const types = new Set(['local', 'online', 'folder', 'local-image', 'online-image']);

  function parseEntry(key, value) {
    try {
      const entry = JSON.parse(value);
      if (entry && types.has(entry.type) && Number.isFinite(entry.createdAt)
          && typeof entry.query === 'string' && typeof entry.folder === 'string') {
        return { ...entry, id: key.slice(prefix.length) };
      }
    } catch {
      // Ignore malformed browser storage entries.
    }
    return null;
  }

  function entryKeys() {
    return Object.keys(localStorage).filter(key => key.startsWith(prefix));
  }

  function record(type, { query = '', folder = '', keywords = '' }) {
    try {
      const createdAt = Date.now();
      const suffix = crypto.getRandomValues(new Uint32Array(2)).join('-');
      localStorage.setItem(prefix + createdAt + '-' + suffix, JSON.stringify({ type, query, folder, keywords, createdAt }));
    } catch {
      // Search remains usable when browser storage is blocked or full.
    }
  }

  function list() {
    return entryKeys()
      .map(key => parseEntry(key, localStorage.getItem(key)))
      .filter(Boolean)
      .sort((first, second) => second.createdAt - first.createdAt);
  }

  function restoredEntry(...acceptedTypes) {
    const id = new URLSearchParams(location.hash.slice(1)).get('history');
    if (!id) return null;

    try {
      const key = prefix + id;
      const entry = parseEntry(key, localStorage.getItem(key));
      return entry && acceptedTypes.includes(entry.type) ? entry : null;
    } catch {
      return null;
    }
  }

  function clear() {
    entryKeys().forEach(key => localStorage.removeItem(key));
  }

  return { record, list, restoredEntry, clear };
})();
