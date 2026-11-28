const historyPage = document.querySelector('.history');
const historyList = document.getElementById('history-list');
const historyStatus = document.getElementById('history-status');
const clearHistory = document.getElementById('clear-history');
const historyDate = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });
const historyLabels = {
  local: 'Local search',
  online: 'Online search',
  folder: 'Folder scan',
  'local-image': 'Local image search',
  'online-image': 'Online image search',
};

function createHistoryItem(entry) {
  const item = document.createElement('li');
  const link = document.createElement('a');
  link.className = 'history__entry';
  const target = entry.type.startsWith('online') ? historyPage.dataset.onlineUrl : historyPage.dataset.localUrl;
  link.href = `${target}#history=${encodeURIComponent(entry.id)}`;

  const description = document.createElement('div');
  description.className = 'history__description';
  const type = document.createElement('span');
  type.className = 'history__meta';
  type.textContent = historyLabels[entry.type];
  const title = document.createElement('strong');
  title.textContent = entry.type === 'folder' ? entry.folder : entry.query;
  description.append(type, title);

  if (entry.type.startsWith('local') && entry.folder) {
    const folder = document.createElement('span');
    folder.className = 'history__meta';
    folder.textContent = entry.folder;
    description.append(folder);
  }

  const timestamp = document.createElement('time');
  timestamp.className = 'history__meta';
  const date = new Date(entry.createdAt);
  timestamp.dateTime = date.toISOString();
  timestamp.textContent = historyDate.format(date);
  link.append(description, timestamp);
  item.append(link);
  return item;
}

function renderHistory() {
  try {
    const entries = searchHistory.list();
    const items = document.createDocumentFragment();
    entries.forEach(entry => items.append(createHistoryItem(entry)));
    historyList.replaceChildren(items);
    historyStatus.textContent = entries.length ? '' : 'Your searches and folder scans will appear here.';
    clearHistory.hidden = entries.length === 0;
  } catch {
    historyList.replaceChildren();
    historyStatus.textContent = 'Search history is unavailable in this browser.';
    clearHistory.hidden = true;
  }
}

clearHistory.addEventListener('click', () => {
  if (!window.confirm('Clear all search and folder history from this browser?')) return;
  try {
    searchHistory.clear();
    renderHistory();
  } catch {
    historyStatus.textContent = 'Could not clear search history. Please try again.';
  }
});

window.addEventListener('pageshow', renderHistory);
window.addEventListener('storage', renderHistory);
renderHistory();
