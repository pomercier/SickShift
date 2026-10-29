/**
 * SickShift Episode Live Preview on Row Hover / Click-Hold
 * Automatically detects default system language, prioritizes Quebec/Canadian French,
 * remembers user audio mute preference (unmuted by default), and displays clean real excerpts.
 */
(function ($) {
    'use strict';

    if (window._sgEpisodePreviewLoaded) return;
    window._sgEpisodePreviewLoaded = true;

    // Detect system language
    const rawLang = (window.SG_SYS_LANG || navigator.language || navigator.userLanguage || 'fr');
    const systemLang = rawLang.split(/[-_.]/)[0].toLowerCase();

    // Sound preference from localStorage: default is UNMUTED (sound active by default)
    const storedMute = localStorage.getItem('sg_preview_muted');
    let userPrefMuted = storedMute !== null ? (storedMute === 'true') : false;

    // Inject CSS styles for the subtle preview popup
    const css = `
    .ep-preview-popup {
        position: fixed;
        width: 390px;
        background: rgba(12, 17, 28, 0.96);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(61, 217, 235, 0.45);
        border-radius: 12px;
        box-shadow: 0 18px 48px rgba(0, 0, 0, 0.8), 0 0 24px rgba(61, 217, 235, 0.22);
        z-index: 99999;
        overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #e6edf3;
        opacity: 0;
        transform: translateY(6px) scale(0.98);
        transition: opacity 180ms cubic-bezier(0.16, 1, 0.3, 1), transform 180ms cubic-bezier(0.16, 1, 0.3, 1);
        pointer-events: auto;
    }
    .ep-preview-popup.visible {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
    .ep-preview-header {
        padding: 9px 14px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.01) 100%);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        text-align: center;
        min-height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .ep-preview-name {
        font-size: 13px;
        font-weight: 600;
        color: #ffffff;
        line-height: 1.35;
        word-break: normal;
        overflow-wrap: break-word;
        text-align: center;
        letter-spacing: 0.2px;
        text-shadow: 0 1px 4px rgba(0,0,0,0.6);
        max-width: 100%;
    }
    .ep-preview-media-wrap {
        position: relative;
        width: 100%;
        height: 220px;
        background: #000000;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }
    .ep-preview-video {
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
        background: #000;
    }
    .ep-preview-spinner {
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: rgba(12, 17, 28, 0.9);
        gap: 10px;
        font-size: 12px;
        color: #8b949e;
        z-index: 5;
        transition: opacity 180ms ease;
    }
    .ep-preview-spinner-ring {
        width: 32px;
        height: 32px;
        border: 3px solid rgba(61, 217, 235, 0.2);
        border-top-color: #3dd9eb;
        border-radius: 50%;
        animation: epSpin 750ms linear infinite;
    }
    @keyframes epSpin {
        to { transform: rotate(360deg); }
    }
    .ep-preview-unmute-overlay {
        position: absolute;
        bottom: 12px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.85);
        border: 1px solid rgba(61, 217, 235, 0.6);
        color: #ffffff;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 500;
        cursor: pointer;
        z-index: 6;
        transition: background 150ms ease, transform 150ms ease;
        white-space: nowrap;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
    }
    .ep-preview-unmute-overlay:hover {
        background: rgba(61, 217, 235, 0.35);
        transform: translateX(-50%) scale(1.03);
    }
    .ep-preview-footer {
        padding: 8px 12px;
        background: rgba(0, 0, 0, 0.5);
        border-top: 1px solid rgba(255, 255, 255, 0.06);
    }
    .ep-preview-controls {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .ep-preview-btn {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.14);
        color: #c9d1d9;
        border-radius: 6px;
        cursor: pointer;
        padding: 4px 8px;
        font-size: 12px;
        line-height: 1;
        transition: all 150ms ease;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .ep-preview-btn:hover {
        background: rgba(61, 217, 235, 0.25);
        border-color: #3dd9eb;
        color: #ffffff;
    }
    .ep-preview-progress-bar {
        flex: 1;
        height: 6px;
        background: rgba(255, 255, 255, 0.16);
        border-radius: 3px;
        position: relative;
        cursor: pointer;
        overflow: hidden;
    }
    .ep-preview-progress-fill {
        height: 100%;
        width: 0%;
        background: linear-gradient(90deg, #3dd9eb, #2eaadc);
        border-radius: 3px;
        transition: width 100ms linear;
    }
    .ep-preview-time-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #adbac7;
        flex-shrink: 0;
        white-space: nowrap;
    }
    /* Subtle row indicator on hover */
    tr[data-has-file="1"],
    #sec-to-watch .show-row {
        cursor: pointer;
        position: relative;
    }
    tr[data-has-file="1"]:hover,
    #sec-to-watch .show-row:hover {
        background-color: rgba(61, 217, 235, 0.06) !important;
    }
    tr[data-has-file="1"].ep-preview-active-row,
    #sec-to-watch .show-row.ep-preview-active-row {
        outline: 1px solid rgba(61, 217, 235, 0.5) !important;
        box-shadow: inset 0 0 12px rgba(61, 217, 235, 0.15) !important;
    }
    `;

    const styleEl = document.createElement('style');
    styleEl.type = 'text/css';
    styleEl.appendChild(document.createTextNode(css));
    document.head.appendChild(styleEl);

    // Build the popup DOM
    const $popup = $(`
        <div id="episodePreviewPopup" class="ep-preview-popup" style="display:none;">
            <div class="ep-preview-header">
                <div class="ep-preview-name">Episode</div>
            </div>
            <div class="ep-preview-media-wrap">
                <div class="ep-preview-spinner">
                    <div class="ep-preview-spinner-ring"></div>
                    <span class="ep-preview-sp-text">Chargement de l'extrait...</span>
                </div>
                <video class="ep-preview-video" playsinline></video>
                <div class="ep-preview-unmute-overlay" style="display:none;">
                    🔇 Son coupé — Cliquez pour activer
                </div>
            </div>
            <div class="ep-preview-footer">
                <div class="ep-preview-controls">
                    <button class="ep-preview-btn ep-preview-btn-play" title="Lecture / Pause">❚❚</button>
                    <button class="ep-preview-btn ep-preview-btn-mute" title="Couper / Activer le son">🔊</button>
                    <div class="ep-preview-progress-bar">
                        <div class="ep-preview-progress-fill"></div>
                    </div>
                    <span class="ep-preview-time-pill ep-preview-time-text">00:00</span>
                </div>
            </div>
        </div>
    `);

    $('body').append($popup);

    const videoEl = $popup.find('.ep-preview-video')[0];
    const $spinner = $popup.find('.ep-preview-spinner');
    const $unmuteOverlay = $popup.find('.ep-preview-unmute-overlay');
    const $progressBar = $popup.find('.ep-preview-progress-bar');
    const $progressFill = $popup.find('.ep-preview-progress-fill');
    const $btnPlay = $popup.find('.ep-preview-btn-play');
    const $btnMute = $popup.find('.ep-preview-btn-mute');
    const $epName = $popup.find('.ep-preview-name');
    const $timeText = $popup.find('.ep-preview-time-text');

    let hoverTimer = null;
    let currentTarget = null;
    let currentClipData = null;
    let previewRequestId = 0;

    function formatTime(s) {
        s = Math.floor(s || 0);
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
    }

    function updateMuteButtonUI() {
        const isMuted = videoEl.muted;
        $btnMute.text(isMuted ? '🔇' : '🔊').attr('title', isMuted ? 'Activer le son' : 'Couper le son');
        if (!isMuted) {
            $unmuteOverlay.hide();
        }
    }

    function positionPopupNear(elem, clientX, clientY) {
        const rect = elem.getBoundingClientRect();
        const popupWidth = 390;
        const popupHeight = 310;
        const margin = 12;

        let left = (clientX !== undefined ? clientX + 16 : rect.right - popupWidth);
        let top = (clientY !== undefined ? clientY - 40 : rect.bottom + 8);

        // Viewport boundaries
        const vw = window.innerWidth;
        const vh = window.innerHeight;

        if (left + popupWidth > vw - margin) {
            left = vw - popupWidth - margin;
        }
        if (left < margin) {
            left = margin;
        }

        if (top + popupHeight > vh - margin) {
            // Flip above row
            top = (clientY !== undefined ? clientY - popupHeight - 16 : rect.top - popupHeight - 8);
        }
        if (top < margin) {
            top = margin;
        }

        $popup.css({ left: `${Math.round(left)}px`, top: `${Math.round(top)}px` });
    }

    function adjustTitleLayout(title) {
        $epName.text(title).attr('title', title);
        const len = title.length;
        if (len > 38) {
            $epName.css('font-size', '11.5px');
        } else if (len > 26) {
            $epName.css('font-size', '12.5px');
        } else {
            $epName.css('font-size', '13.5px');
        }
    }

    function isDeleteColumnZone(row, clientX, clientY, e) {
        if (e && e.target && $(e.target).closest('.col-delete, .ep-delete-btn, th.col-delete').length > 0) {
            return true;
        }
        if (!row) return false;
        const colDel = row.querySelector ? (row.querySelector('.col-delete') || row.querySelector('.ep-delete-btn')) : null;
        if (colDel) {
            const rect = colDel.getBoundingClientRect();
            // Entire equivalent width of the delete column and 20px leading boundary
            if (clientX !== undefined && clientX >= (rect.left - 20)) {
                return true;
            }
        }
        return false;
    }

    let currentMouseX = null;
    let currentMouseY = null;
    $(document).on('mousemove', function (e) {
        currentMouseX = e.clientX;
        currentMouseY = e.clientY;
    });

    function showPopupFor(row, clientX, clientY, forceFresh = false) {
        if (clientX !== undefined && isDeleteColumnZone(row, clientX, clientY)) {
            return;
        }
        const $row = $(row);
        const indexer = $row.data('indexer') || 1;
        const showId = $row.data('show-id');
        const season = $row.data('season');
        const episode = $row.data('episode');

        // Extract clean full episode name
        let epTitle = $row.data('ep-name') || $row.find('.col-epname, .col-name').clone().children('img').remove().end().text().trim();
        if (!epTitle) {
            epTitle = $row.find('.col-epname, .col-name').text().trim() || 'Episode';
        }
        let showTitle = $row.data('show-name') || $('#showtitle').data('showname') || '';
        let fullTitle = epTitle;
        if (showTitle && !epTitle.toLowerCase().startsWith(showTitle.toLowerCase())) {
            fullTitle = `${showTitle} — ${epTitle}`;
        }
        adjustTitleLayout(fullTitle);

        if (!indexer || !showId || season === undefined || episode === undefined) {
            return;
        }

        if (currentTarget === row && !forceFresh && $popup.hasClass('visible')) {
            return;
        }

        currentTarget = row;
        const requestId = ++previewRequestId;
        $('tr.ep-preview-active-row, .show-row.ep-preview-active-row').removeClass('ep-preview-active-row');
        $row.addClass('ep-preview-active-row');

        // Set full episode title with subtle font scaling
        adjustTitleLayout(epTitle);
        $timeText.text('Chargement...');

        // Position and show container
        if (clientX !== undefined || clientY !== undefined || !$popup.hasClass('visible')) {
            positionPopupNear(row, clientX, clientY);
        }
        $popup.show();
        $popup[0].offsetHeight;
        $popup.addClass('visible');

        // Immediately fade out background music as the popup appears
        if (window.fadeGlobalSoundtrackOut) {
            window.fadeGlobalSoundtrackOut(450);
        }

        // Show spinner
        $spinner.find('.ep-preview-sp-text').text('Préparation de l’extrait...');
        $spinner.stop(true, true).show().css('opacity', '1');
        $unmuteOverlay.hide();
        $progressFill.css('width', '0%');

        // Pause existing video
        videoEl.pause();
        videoEl.removeAttribute('src');
        videoEl.load();

        // Fetch clip info
        const root = (window.sbRoot || '').replace(/\/$/, '');
        const apiUrl = `${root}/dashboard/api/preview-clip-info/${indexer}/${showId}/${season}/${episode}?sys_lang=${encodeURIComponent(systemLang)}${forceFresh ? '&fresh=true' : ''}`;

        $.ajax({
            url: apiUrl,
            method: 'GET',
            dataType: 'json',
            // ffprobe may take 10s and a heavy source up to 60s to convert.
            timeout: 75000,
            success: function (data) {
                if (currentTarget !== row || requestId !== previewRequestId) return;
                currentClipData = data;

                $timeText.text(`Extrait à ${data.start_formatted || '00:00'}`);

                // Load video source
                videoEl.src = data.video_url;
                videoEl.load();

                // Apply user audio preference (default: UNMUTED)
                videoEl.muted = userPrefMuted;
                updateMuteButtonUI();

                if (window.fadeGlobalSoundtrackOut) {
                    window.fadeGlobalSoundtrackOut();
                }

                const playPromise = videoEl.play();
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        if (currentTarget !== row || requestId !== previewRequestId) return;
                        $spinner.fadeOut(150);
                        $btnPlay.text('❚❚');
                    }).catch((err) => {
                        if (currentTarget !== row || requestId !== previewRequestId || err.name === 'AbortError') return;
                        // If browser autoplay policy blocks unmuted audio before any user click on page,
                        // fallback to muted and offer clear unmute pill
                        if (err.name === 'NotAllowedError') {
                            videoEl.muted = true;
                            updateMuteButtonUI();
                            $unmuteOverlay.show();
                            videoEl.play().catch((mutedError) => {
                                if (currentTarget === row && requestId === previewRequestId && mutedError.name !== 'AbortError') {
                                    showPlaybackError();
                                }
                            });
                        } else {
                            showPlaybackError();
                        }
                    });
                }
            },
            error: function (xhr) {
                if (currentTarget !== row || requestId !== previewRequestId) return;
                $spinner.find('.ep-preview-sp-text').text("Extrait indisponible");
                setTimeout(() => {
                    if (currentTarget === row && requestId === previewRequestId) hidePopup();
                }, 1500);
            }
        });
    }

    function hidePopup() {
        ++previewRequestId;
        clearTimeout(hoverTimer);
        $popup.removeClass('visible');
        videoEl.pause();
        videoEl.removeAttribute('src');
        videoEl.load();
        $popup.hide();
        currentTarget = null;
        $('tr.ep-preview-active-row, .show-row.ep-preview-active-row').removeClass('ep-preview-active-row');
        if (window.fadeGlobalSoundtrackIn) {
            window.fadeGlobalSoundtrackIn();
        }
    }

    // Video events
    function showPlaybackError() {
        $spinner.find('.ep-preview-sp-text').text('Lecture de l’extrait impossible');
        $spinner.stop(true, true).show().css('opacity', '1');
        $btnPlay.text('▶');
    }

    videoEl.addEventListener('error', () => {
        if (currentTarget && videoEl.getAttribute('src')) showPlaybackError();
    });

    videoEl.addEventListener('timeupdate', () => {
        if (!videoEl.duration) return;
        const pct = (videoEl.currentTime / videoEl.duration) * 100;
        $progressFill.css('width', `${pct}%`);
    });

    videoEl.addEventListener('ended', () => {
        videoEl.currentTime = 0;
        videoEl.play().catch(() => {});
    });

    videoEl.addEventListener('playing', () => {
        $spinner.fadeOut(150);
        $btnPlay.text('❚❚');
    });

    videoEl.addEventListener('pause', () => {
        $btnPlay.text('▶');
    });

    // Controls
    $btnPlay.on('click', function (e) {
        e.stopPropagation();
        if (videoEl.paused) {
            videoEl.play();
        } else {
            videoEl.pause();
        }
    });

    $btnMute.on('click', function (e) {
        e.stopPropagation();
        videoEl.muted = !videoEl.muted;
        userPrefMuted = videoEl.muted;
        localStorage.setItem('sg_preview_muted', userPrefMuted);
        updateMuteButtonUI();
    });

    $unmuteOverlay.on('click', function (e) {
        e.stopPropagation();
        videoEl.muted = false;
        userPrefMuted = false;
        localStorage.setItem('sg_preview_muted', false);
        updateMuteButtonUI();
        $unmuteOverlay.fadeOut(150);
    });

    $progressBar.on('click', function (e) {
        e.stopPropagation();
        if (!videoEl.duration) return;
        const rect = this.getBoundingClientRect();
        const pos = (e.clientX - rect.left) / rect.width;
        videoEl.currentTime = pos * videoEl.duration;
    });

    const ROW_SELECTOR = 'tr[data-has-file="1"], #sec-to-watch .show-row[data-has-file="1"], #sec-to-watch .show-row';
    let rowMouseDownTimer = null;
    let isHoldTriggered = false;

    // Row interaction bindings
    $(document).on('mouseenter', ROW_SELECTOR, function (e) {
        clearTimeout(hoverTimer);
        currentMouseX = e.clientX;
        currentMouseY = e.clientY;

        // Entire delete column equivalent exclusion
        if (isDeleteColumnZone(this, e.clientX, e.clientY, e)) {
            return;
        }

        const row = this;
        const clientX = e.clientX;
        const clientY = e.clientY;

        // Dwell hover trigger (~380ms)
        hoverTimer = setTimeout(() => {
            if (currentMouseX !== null && isDeleteColumnZone(row, currentMouseX, currentMouseY)) {
                return;
            }
            showPopupFor(row, clientX, clientY);
        }, 380);
    });

    // Cancel / hide if moving into the entire delete column zone
    $(document).on('mousemove', ROW_SELECTOR, function (e) {
        currentMouseX = e.clientX;
        currentMouseY = e.clientY;
        if (isDeleteColumnZone(this, e.clientX, e.clientY, e)) {
            clearTimeout(hoverTimer);
            if (currentTarget === this) {
                hidePopup();
            }
        }
    });

    // Direct interception on the entire delete column and button
    $(document).on('mouseenter mousemove mousedown', 'td.col-delete, th.col-delete, .ep-delete-btn', function (e) {
        clearTimeout(hoverTimer);
        if ($popup.hasClass('visible')) {
            hidePopup();
        }
    });

    // "Assure toi que si je déplace ça arrete":
    // As soon as the mouse moves out of the row, stop immediately!
    $(document).on('mouseleave', ROW_SELECTOR, function (e) {
        clearTimeout(hoverTimer);
        clearTimeout(rowMouseDownTimer);
        // If moving onto the popup itself, allow user to interact with player
        const toElem = e.relatedTarget;
        if (toElem && $(toElem).closest('#episodePreviewPopup').length > 0) {
            return;
        }
        hidePopup();
    });

    // If mouse leaves the popup, stop immediately!
    $popup.on('mouseleave', function () {
        hidePopup();
    });

    // Long click / "clic qui traîne" / mouse down hold on row
    $(document).on('mousedown', ROW_SELECTOR, function (e) {
        if ($(e.target).closest('input, a, button, select, .meta, .col-search, .col-delete, .ep-delete-btn').length > 0 ||
            isDeleteColumnZone(this, e.clientX, e.clientY, e)) {
            clearTimeout(hoverTimer);
            clearTimeout(rowMouseDownTimer);
            return;
        }
        clearTimeout(hoverTimer);
        clearTimeout(rowMouseDownTimer);
        isHoldTriggered = false;

        const row = this;
        const clientX = e.clientX;
        const clientY = e.clientY;

        // "Le clic qui traine": triggers the identical video popup after 200ms of holding
        rowMouseDownTimer = setTimeout(() => {
            isHoldTriggered = true;
            showPopupFor(row, clientX, clientY);
        }, 200);
    });

    $(document).on('mouseup', ROW_SELECTOR, function (e) {
        clearTimeout(rowMouseDownTimer);
    });

    $(document).on('click', ROW_SELECTOR, function (e) {
        if ($(e.target).closest('input, a, button, select, .meta, .col-search, .col-delete, .ep-delete-btn').length > 0 ||
            isDeleteColumnZone(this, e.clientX, e.clientY, e)) {
            clearTimeout(hoverTimer);
            return;
        }
        // If the click lingered ("clic qui traine") or video popup is showing, cancel navigation
        if (isHoldTriggered || $popup.hasClass('visible')) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    });

    // Close on escape key
    $(document).on('keydown', function (e) {
        if (e.key === 'Escape' && $popup.hasClass('visible')) {
            hidePopup();
        }
    });

    // Close if clicking outside
    $(document).on('click', function (e) {
        if ($popup.hasClass('visible') && !$(e.target).closest('#episodePreviewPopup, tr[data-has-file="1"], #sec-to-watch .show-row').length) {
            hidePopup();
        }
    });

    window.isEpPreviewShowing = function () {
        return $popup && $popup.hasClass('visible');
    };

    window.triggerEpisodePreview = function (rowOrEl, clientX, clientY) {
        if (rowOrEl) {
            showPopupFor(rowOrEl, clientX, clientY);
        }
    };

})(jQuery);
