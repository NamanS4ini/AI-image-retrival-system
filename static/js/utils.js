// =====================================================
// UTILITY FUNCTIONS & HTML BUILDERS
// =====================================================

/**
 * Normalizes CLIP cosine similarity [0.12, 0.32] to an intuitive 0-100% confidence scale.
 */
function formatConfidence(rawScore, mode) {
  if (rawScore == null) return null;
  if (mode === 'image') return Math.round(Math.min(Math.max(rawScore, 0), 1) * 100);
  const min = 0.12;
  const max = 0.32;
  const normalized = Math.min(Math.max((rawScore - min) / (max - min), 0), 1);
  return Math.round(normalized * 100);
}

function searchResultContext(data) {
  const query = `"<strong>${esc(data.query)}</strong>"`;
  if (data.mode !== 'image') return `for ${query}`;
  const keywords = data.keywords ? ` · Stock-photo keywords: <strong>${esc(data.keywords)}</strong>` : '';
  return `similar to ${query}${keywords}`;
}

/**
 * Safely escape HTML entities.
 */
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML.replace(/"/g, '&quot;');
}

/**
 * Format total seconds to human-readable timestamp (e.g. 14.5 -> "0:14", 75 -> "1:15", 3665 -> "1:01:05").
 */
function formatTime(totalSeconds) {
  if (totalSeconds == null || isNaN(totalSeconds)) return '0:00';
  const sec = Math.floor(totalSeconds);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  const formattedS = s < 10 ? '0' + s : s;
  if (m >= 60) {
    const h = Math.floor(m / 60);
    const remM = m % 60;
    const formattedM = remM < 10 ? '0' + remM : remM;
    return `${h}:${formattedM}:${formattedS}`;
  }
  return `${m}:${formattedS}`;
}

/**
 * Render loading dots state.
 */
function loadingHTML() {
  return `<div class="state">
    <div class="state__dots">
      <div class="state__dot"></div>
      <div class="state__dot"></div>
      <div class="state__dot"></div>
    </div>
    <div class="state__text">Searching...</div>
  </div>`;
}

/**
 * Render empty state with custom or default message.
 */
function emptyHTML(msg) {
  return `<div class="state">
    <div class="state__title">No matches found</div>
    <div class="state__text">${esc(msg || 'Try different or broader search terms.')}</div>
  </div>`;
}

/**
 * Render error state message.
 */
function errorHTML(message) {
  return `<div class="state" role="alert">
    <div class="state__title">Search unavailable</div>
    <div class="state__text">${esc(message || 'Something went wrong. Please try again.')}</div>
  </div>`;
}

// =====================================================
// MEDIA MODAL CONTROLLER (IMAGES & VIDEOS)
// =====================================================

function openImageModal(imgSrc, filename, score, downloadUrl) {
  const modal = document.getElementById('video-modal');
  const player = document.getElementById('video-modal-player');
  const imageEl = document.getElementById('video-modal-image');
  const title = document.getElementById('video-modal-title');
  const badge = document.getElementById('video-modal-badge');
  const replayBtn = document.getElementById('video-modal-replay');
  const downloadBtn = document.getElementById('video-modal-download');
  const downloadText = document.getElementById('video-modal-download-text');

  if (!modal) return;

  if (title) {
    title.textContent = filename || 'Image Preview';
    title.title = filename || '';
  }

  if (badge) {
    if (score != null) {
      badge.textContent = `${score}% Match`;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  }

  // Switch to image view
  if (player) {
    player.pause();
    player.style.display = 'none';
    player.removeAttribute('src');
  }

  if (imageEl) {
    imageEl.src = imgSrc;
    imageEl.alt = filename || 'Image Preview';
    imageEl.style.display = 'block';
  }

  if (replayBtn) replayBtn.style.display = 'none';

  if (downloadBtn) {
    downloadBtn.href = downloadUrl || imgSrc;
    downloadBtn.download = filename || 'image';
  }
  if (downloadText) downloadText.textContent = 'Save Image';

  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function openVideoModal(mediaPath, filename, timestamp) {
  const modal = document.getElementById('video-modal');
  const player = document.getElementById('video-modal-player');
  const imageEl = document.getElementById('video-modal-image');
  const title = document.getElementById('video-modal-title');
  const badge = document.getElementById('video-modal-badge');
  const jumpTime = document.getElementById('video-modal-jump-time');
  const downloadBtn = document.getElementById('video-modal-download');
  const downloadText = document.getElementById('video-modal-download-text');
  const replayBtn = document.getElementById('video-modal-replay');

  if (!modal || !player) return;

  const targetTime = Math.max(parseFloat(timestamp) || 0, 0);
  const formattedTime = formatTime(targetTime);

  if (title) {
    title.textContent = filename || 'Video Preview';
    title.title = filename || '';
  }
  if (badge) {
    badge.textContent = `Matched at ${formattedTime}`;
    badge.style.display = 'inline-block';
  }
  if (jumpTime) jumpTime.textContent = formattedTime;

  // Switch to video view
  if (imageEl) {
    imageEl.style.display = 'none';
    imageEl.removeAttribute('src');
  }

  player.style.display = 'block';

  if (downloadBtn) {
    downloadBtn.href = `/local-image?path=${encodeURIComponent(mediaPath)}`;
    downloadBtn.download = filename || 'video';
  }
  if (downloadText) downloadText.textContent = 'Save Video';

  if (replayBtn) {
    replayBtn.style.display = 'inline-flex';
    replayBtn.onclick = () => {
      player.currentTime = targetTime;
      player.play().catch(() => {});
    };
  }

  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';

  const videoUrl = `/local-image?path=${encodeURIComponent(mediaPath)}`;
  player.src = videoUrl;

  player.onloadedmetadata = () => {
    player.currentTime = targetTime;
    player.play().catch(() => {});
  };
}

function closeMediaModal() {
  const modal = document.getElementById('video-modal');
  const player = document.getElementById('video-modal-player');
  const imageEl = document.getElementById('video-modal-image');

  if (modal) {
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
  if (player) {
    player.pause();
    player.removeAttribute('src');
    player.load();
  }
  if (imageEl) {
    imageEl.removeAttribute('src');
  }
}

// Modal event listeners
document.addEventListener('DOMContentLoaded', () => {
  const modalCloseBtn = document.getElementById('video-modal-close');
  const modalBackdrop = document.getElementById('video-modal-backdrop');

  if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeMediaModal);
  if (modalBackdrop) modalBackdrop.addEventListener('click', closeMediaModal);

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeMediaModal();
    }
  });
});
