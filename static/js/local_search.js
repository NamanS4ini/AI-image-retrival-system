// =====================================================
// LOCAL FOLDER SCANNING & SEMANTIC SEARCH
// =====================================================

const scanBtn = document.getElementById('scan-btn');
const folderInput = document.getElementById('folder-path');
const scanProgress = document.getElementById('scan-progress');
const scanLabel = document.getElementById('scan-label');
const scanCount = document.getElementById('scan-count');
const scanFill = document.getElementById('scan-fill');
const scanDone = document.getElementById('scan-done');
const scanDoneText = document.getElementById('scan-done-text');
const scanError = document.getElementById('scan-error');
const historyFolderHelp = document.getElementById('history-folder-help');
const localSearch = document.getElementById('local-search');

const localSearchBtn = document.getElementById('local-search-btn');
const localQueryInput = document.getElementById('local-query');
const localGallery = document.getElementById('local-gallery');
const localStats = document.getElementById('local-stats');
const localStatsText = document.getElementById('local-stats-text');
const localMinConfidence = document.getElementById('local-min-confidence');

let pollTimer = null;
let lastLocalData = null;
let indexedFolder = '';

const restoredLocalSearch = searchHistory.restoredEntry('local', 'folder', 'local-image');
let pendingHistoryFolder = restoredLocalSearch?.folder || '';
if (restoredLocalSearch) {
  folderInput.value = pendingHistoryFolder;
  if (restoredLocalSearch.type === 'local') localQueryInput.value = restoredLocalSearch.query;
  historyFolderHelp.hidden = !pendingHistoryFolder;
}

if (scanBtn) scanBtn.addEventListener('click', startScan);
if (folderInput) {
  folderInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') startScan();
  });
}

if (localSearchBtn) localSearchBtn.addEventListener('click', () => searchLocal());
if (localQueryInput) {
  localQueryInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') searchLocal();
  });
}

if (localMinConfidence) {
  localMinConfidence.addEventListener('change', () => {
    if (lastLocalData) renderLocalResults(lastLocalData);
  });
}

setupImageSearch(searchLocal, restoredLocalSearch);

async function checkExistingScan() {
  try {
    const res = await fetch('/scan-status');
    if (!res.ok) return;
    const s = await res.json();
    if (scanBtn.disabled) return;
    if (s.scanning) {
      if (!folderInput.value) folderInput.value = s.folder || '';
      scanBtn.disabled = true;
      scanBtn.textContent = 'Scanning…';
      showProgress();
      startPolling();
    } else if (s.complete && s.folder && s.total > 0) {
      if (!folderInput.value) folderInput.value = s.folder;
      showScanDone(s.total, s.folder);
    }
  } catch (e) {
    /* ignore */
  }
}

async function startScan() {
  if (scanBtn.disabled || localSearchBtn.disabled) return;
  const folder = folderInput.value.trim();
  if (!folder) {
    folderInput.focus();
    return;
  }

  searchHistory.record('folder', { folder });
  scanBtn.disabled = true;
  scanBtn.textContent = 'Scanning…';
  scanError.hidden = true;
  scanDone.style.display = 'none';
  localSearch.style.display = 'none';
  indexedFolder = '';
  localGallery.innerHTML = '';
  localStats.style.display = 'none';
  lastLocalData = null;

  try {
    const res = await fetch('/scan-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder })
    });
    const data = await res.json();

    if (!res.ok) {
      showScanError(data.error || 'Failed to start scan.');
      scanBtn.disabled = false;
      scanBtn.textContent = 'Scan folder';
      return;
    }

    pendingHistoryFolder = '';
    historyFolderHelp.hidden = true;
    showProgress();
    startPolling();
  } catch (e) {
    showScanError('Could not connect to the server.');
    scanBtn.disabled = false;
    scanBtn.textContent = 'Scan folder';
  }
}

function showScanError(message) {
  scanError.textContent = message;
  scanError.hidden = false;
}

function showProgress() {
  scanProgress.style.display = 'block';
  scanFill.style.width = '0%';
  scanCount.textContent = '0 / 0';
  scanLabel.textContent = 'Scanning photos and videos…';
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const res = await fetch('/scan-status');
      if (!res.ok) return;
      const s = await res.json();

      if (s.total > 0) {
        const pct = Math.round((s.processed / s.total) * 100);
        scanFill.style.width = pct + '%';
        scanCount.textContent = s.processed + ' / ' + s.total;
      }

      if (!s.scanning) {
        clearInterval(pollTimer);
        pollTimer = null;
        scanProgress.style.display = 'none';
        scanBtn.disabled = false;
        scanBtn.textContent = 'Scan folder';

        if (s.error) {
          showScanError(s.error);
        } else if (s.complete) {
          showScanDone(s.total, s.folder);
          if (indexedFolder) localQueryInput.focus();
        }
      }
    } catch (e) {
      /* ignore */
    }
  }, 400);
}

function showScanDone(count, folder) {
  if (pendingHistoryFolder && pendingHistoryFolder !== folder) return;
  indexedFolder = folder;
  pendingHistoryFolder = '';
  historyFolderHelp.hidden = true;
  const folderName = folder.split(/[/\\]/).filter(Boolean).pop() || folder;
  scanDoneText.innerHTML = `Scan complete. ${count} ${count === 1 ? 'file' : 'files'} checked in <span class="folder-name">${esc(folderName)}</span>.`;
  scanDone.style.display = 'block';
  localSearch.style.display = 'block';
}

async function searchLocal(imageData = null, endpoint = '/search-local') {
  if (localSearchBtn.disabled) return;
  const query = imageData ? imageData.get('image').name : localQueryInput.value.trim();
  if (!query) {
    localQueryInput.focus();
    return;
  }

  searchHistory.record(imageData ? 'local-image' : 'local', { query, folder: indexedFolder });
  localSearchBtn.classList.add('loading');
  localSearchBtn.disabled = true;
  lastLocalData = null;
  localStats.style.display = 'none';
  localGallery.innerHTML = loadingHTML();

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: imageData ? undefined : { 'Content-Type': 'application/json' },
      body: imageData || JSON.stringify({ query })
    });
    const data = await res.json();
    if (!res.ok) {
      localGallery.innerHTML = errorHTML(data.error);
      return;
    }
    lastLocalData = data;
    renderLocalResults(data);
  } catch (e) {
    localGallery.innerHTML = errorHTML();
    console.error(e);
  } finally {
    localSearchBtn.classList.remove('loading');
    localSearchBtn.disabled = false;
  }
}

function renderLocalResults(data) {
  localGallery.innerHTML = '';

  if (!data.images || data.images.length === 0) {
    localStats.style.display = 'none';
    localGallery.innerHTML = emptyHTML();
    return;
  }

  const minConf = parseInt(localMinConfidence.value, 10);
  const filtered = data.images.filter(img => {
    const conf = formatConfidence(img.score, data.mode);
    return conf !== null && conf >= minConf;
  });

  localStats.style.display = 'flex';
  localStatsText.innerHTML = `<strong>${filtered.length}</strong> ${
    filtered.length === 1 ? 'result' : 'results'
  }${minConf > 0 ? ` (min ${minConf}%)` : ''} ${searchResultContext(data)}`;

  if (filtered.length === 0) {
    localGallery.innerHTML = emptyHTML(
      `No files met the minimum match score of ${minConf}%. Try lowering the filter above.`
    );
    return;
  }

  filtered.forEach(img => {
    const score = formatConfidence(img.score, data.mode);
    const isVideo = img.type === 'video';
    const card = document.createElement('div');
    card.className = 'card' + (isVideo ? ' card--video' : '');

    const imgSrc = isVideo
      ? `/local-video-frame?path=${encodeURIComponent(img.path)}&timestamp=${img.timestamp || 0}`
      : `/local-image?path=${encodeURIComponent(img.path)}`;

    const badgeHTML = isVideo
      ? `<span class="card__badge card__badge--video">Video • ${formatTime(img.timestamp)}</span>`
      : `<span class="card__badge">Local</span>`;

    const subInfoHTML = isVideo
      ? `<div class="card__subinfo">Matched at <strong>${formatTime(img.timestamp)}</strong>${
          img.duration ? ` / ${formatTime(img.duration)}` : ''
        }</div>`
      : '';

    const playOverlayHTML = isVideo
      ? `<div class="card__play-icon" aria-hidden="true">
           <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"/></svg>
         </div>`
      : '';

    const openActionHTML = isVideo
      ? `<button type="button" class="btn-sm btn-sm--outline btn-play-video">
           <svg viewBox="0 0 24 24" fill="currentColor">
             <polygon points="5 3 19 12 5 21 5 3"/>
           </svg>
           Play at ${formatTime(img.timestamp)}
         </button>`
      : `<button type="button" class="btn-sm btn-sm--outline btn-preview-image">
           <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
             <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
             <circle cx="12" cy="12" r="3"></circle>
           </svg>
           Preview
         </button>`;

    card.innerHTML = `
      <div class="card__img-wrap" title="Click to preview">
        <img class="card__img" src="${imgSrc}" alt="${esc(img.filename)}" loading="lazy">
        ${playOverlayHTML}
        ${score != null ? `<span class="card__score">${score}%</span>` : ''}
      </div>
      <div class="card__body">
        <div class="card__row">
          <span class="card__name" title="${esc(img.filename)}">${esc(img.filename)}</span>
          ${badgeHTML}
        </div>
        ${subInfoHTML}
        <div class="card__actions">
          ${openActionHTML}
          <a class="btn-sm btn-sm--primary" href="/local-image?path=${encodeURIComponent(
            img.path
          )}" download="${esc(img.filename)}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Save Copy
          </a>
        </div>
      </div>
    `;

    const imgWrap = card.querySelector('.card__img-wrap');
    if (imgWrap) {
      imgWrap.style.cursor = 'pointer';
      imgWrap.addEventListener('click', () => {
        if (isVideo) {
          openVideoModal(img.path, img.filename, img.timestamp);
        } else {
          openImageModal(
            `/local-image?path=${encodeURIComponent(img.path)}`,
            img.filename,
            score,
            `/local-image?path=${encodeURIComponent(img.path)}`
          );
        }
      });
    }

    if (isVideo) {
      const playBtn = card.querySelector('.btn-play-video');
      if (playBtn) {
        playBtn.addEventListener('click', (e) => {
          e.preventDefault();
          openVideoModal(img.path, img.filename, img.timestamp);
        });
      }
    } else {
      const previewBtn = card.querySelector('.btn-preview-image');
      if (previewBtn) {
        previewBtn.addEventListener('click', (e) => {
          e.preventDefault();
          openImageModal(
            `/local-image?path=${encodeURIComponent(img.path)}`,
            img.filename,
            score,
            `/local-image?path=${encodeURIComponent(img.path)}`
          );
        });
      }
    }

    localGallery.appendChild(card);
  });
}

checkExistingScan();
