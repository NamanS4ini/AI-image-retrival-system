// =====================================================
// ONLINE STOCK PHOTO SEARCH & CLIP RANKING
// =====================================================

const onlineSearchBtn = document.getElementById('online-search-btn');
const onlineQueryInput = document.getElementById('online-query');
const onlineGallery = document.getElementById('online-gallery');
const onlineStats = document.getElementById('online-stats');
const onlineStatsText = document.getElementById('online-stats-text');
const onlineMinConfidence = document.getElementById('online-min-confidence');

let lastOnlineData = null;

const restoredOnlineSearch = searchHistory.restoredEntry('online', 'online-image');
if (restoredOnlineSearch?.type === 'online') onlineQueryInput.value = restoredOnlineSearch.query;
setupImageSearch(searchOnline, restoredOnlineSearch);

if (onlineSearchBtn) onlineSearchBtn.addEventListener('click', () => searchOnline());
if (onlineQueryInput) {
  onlineQueryInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') searchOnline();
  });
}

if (onlineMinConfidence) {
  onlineMinConfidence.addEventListener('change', () => {
    if (lastOnlineData) renderOnlineResults(lastOnlineData);
  });
}

async function searchOnline(imageData = null, endpoint = '/search') {
  if (onlineSearchBtn.disabled) return;
  const query = imageData ? imageData.get('image').name : onlineQueryInput.value.trim();
  if (!query) {
    onlineQueryInput.focus();
    return;
  }

  const keywords = imageData ? imageData.get('keywords').trim() : '';
  searchHistory.record(imageData ? 'online-image' : 'online', { query, keywords });
  onlineSearchBtn.classList.add('loading');
  onlineSearchBtn.disabled = true;
  lastOnlineData = null;
  onlineStats.style.display = 'none';
  onlineGallery.innerHTML = loadingHTML();

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: imageData ? undefined : { 'Content-Type': 'application/json' },
      body: imageData || JSON.stringify({ query })
    });
    const data = await res.json();
    if (!res.ok) {
      onlineGallery.innerHTML = errorHTML(data.error);
      return;
    }
    lastOnlineData = data;
    renderOnlineResults(data);
  } catch (e) {
    onlineGallery.innerHTML = errorHTML();
    console.error(e);
  } finally {
    onlineSearchBtn.classList.remove('loading');
    onlineSearchBtn.disabled = false;
  }
}

function renderOnlineResults(data) {
  onlineGallery.innerHTML = '';

  if (!data.images || data.images.length === 0) {
    onlineStats.style.display = 'none';
    const message = data.mode === 'image'
      ? `No stock photos were available for “${data.keywords}”. Try supplying different keywords or check that a provider is configured.`
      : undefined;
    onlineGallery.innerHTML = emptyHTML(message);
    return;
  }

  const minConf = parseInt(onlineMinConfidence.value, 10);
  const filtered = data.images.filter(img => {
    const conf = formatConfidence(img.score, data.mode);
    return conf !== null && conf >= minConf;
  });

  onlineStats.style.display = 'flex';
  onlineStatsText.innerHTML = `<strong>${filtered.length}</strong> ${
    filtered.length === 1 ? 'result' : 'results'
  }${minConf > 0 ? ` (min ${minConf}%)` : ''} ${searchResultContext(data)}`;

  if (filtered.length === 0) {
    onlineGallery.innerHTML = emptyHTML(
      `No photos met the minimum match score of ${minConf}%. Try lowering the filter above.`
    );
    return;
  }

  filtered.forEach(img => {
    const score = formatConfidence(img.score, data.mode);
    const card = document.createElement('div');
    card.className = 'card';
    const previewTitle = img.photographer
      ? `${img.photographer} (${img.site || 'Online'})`
      : 'Online Image';

    card.innerHTML = `
      <button class="card__img-wrap" type="button" aria-label="Preview ${esc(previewTitle)}">
        <img class="card__img" src="${esc(img.url || '')}" alt="${esc(
      data.query
    )}" loading="lazy">
        ${score != null ? `<span class="card__score">${score}%</span>` : ''}
      </button>
      <div class="card__body">
        <div class="card__row">
          <span class="card__name">${esc(img.photographer || 'Unknown')}</span>
          <span class="card__badge">${esc(img.site || '')}</span>
        </div>
        <div class="card__actions">
          <a class="btn-sm btn-sm--outline" href="${
            esc(img.source || '#')
          }" target="_blank" rel="noopener">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
            Source
          </a>
          <a class="btn-sm btn-sm--primary" href="${
            esc(img.download || '#')
          }" target="_blank" rel="noopener" download>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Download
          </a>
        </div>
      </div>
    `;

    const imgWrap = card.querySelector('.card__img-wrap');
    if (imgWrap) {
      imgWrap.style.cursor = 'pointer';
      imgWrap.addEventListener('click', () => {
        openImageModal(
          img.download || img.url,
          previewTitle,
          score,
          img.download || img.url
        );
      });
    }

    onlineGallery.appendChild(card);
  });
}
