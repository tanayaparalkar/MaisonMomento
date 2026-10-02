/**
 * Maison Moménto — Apple Spotlight Search Experience
 * Live AJAX search, keyboard navigation (↑/↓/↵/ESC/Cmd+K), focus trap, and animations.
 */
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('spotlight-search-overlay');
    if (!overlay) return;

    const backdrop = document.getElementById('spotlight-backdrop');
    const modal = document.getElementById('spotlight-modal');
    const input = document.getElementById('spotlight-input');
    const loader = document.getElementById('spotlight-loader');
    const clearBtn = document.getElementById('spotlight-clear-btn');
    const closeBtn = document.getElementById('spotlight-close-btn');
    const resultsList = document.getElementById('spotlight-results-list');
    const resultsCount = document.getElementById('spotlight-results-count');
    const emptyState = document.getElementById('spotlight-empty-state');
    const quickTagsContainer = document.getElementById('spotlight-quick-tags');
    const tagPills = document.querySelectorAll('.spotlight-tag-pill, .spotlight-empty-pill');

    // Search triggers across the page (Navbar search icon, etc.)
    const searchTriggers = document.querySelectorAll(
        '#spotlight-search-trigger, .sf-search-trigger, [aria-label="Search"]'
    );

    let currentAbortController = null;
    let activeCardIndex = -1;
    let lastActiveElement = null;

    // -------------------------------------------------------------------------
    // Open & Close Handlers
    // -------------------------------------------------------------------------
    const openSpotlight = () => {
        lastActiveElement = document.activeElement;
        overlay.classList.add('is-open');
        overlay.setAttribute('aria-hidden', 'false');
        document.body.classList.add('spotlight-open');

        searchTriggers.forEach(btn => btn.setAttribute('aria-expanded', 'true'));

        // Focus search input automatically
        setTimeout(() => {
            input.focus();
            if (input.value) {
                input.select();
            }
        }, 50);

        // Load initial featured items if list is empty
        if (!resultsList.children.length && !input.value.trim()) {
            executeSearch('');
        }
    };

    const closeSpotlight = () => {
        overlay.classList.remove('is-open');
        overlay.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('spotlight-open');

        searchTriggers.forEach(btn => btn.setAttribute('aria-expanded', 'false'));

        if (lastActiveElement && typeof lastActiveElement.focus === 'function') {
            lastActiveElement.focus();
        }
    };

    // Attach open handler to triggers
    searchTriggers.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            openSpotlight();
        });
    });

    // Close on backdrop click (click outside)
    backdrop.addEventListener('click', closeSpotlight);

    // Close on close button click
    if (closeBtn) {
        closeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            closeSpotlight();
        });
    }

    // Clear button
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            input.value = '';
            clearBtn.style.display = 'none';
            input.focus();
            executeSearch('');
        });
    }

    // -------------------------------------------------------------------------
    // Quick Tag Pills
    // -------------------------------------------------------------------------
    tagPills.forEach(pill => {
        pill.addEventListener('click', () => {
            const query = pill.getAttribute('data-query') || pill.textContent.trim();
            input.value = query;
            if (clearBtn) clearBtn.style.display = 'inline-flex';
            input.focus();
            executeSearch(query);
        });
    });

    // -------------------------------------------------------------------------
    // AJAX Live Search
    // -------------------------------------------------------------------------
    let debounceTimer = null;
    const debounceDelay = 220; // Fast, responsive live search

    const executeSearch = (rawQuery) => {
        const query = (rawQuery || '').trim();

        // Update clear button
        if (clearBtn) {
            clearBtn.style.display = rawQuery.length > 0 ? 'inline-flex' : 'none';
        }

        // Cancel previous request
        if (currentAbortController) {
            currentAbortController.abort();
        }
        currentAbortController = new AbortController();

        // Show subtle loader
        if (loader) loader.classList.add('is-active');

        const searchUrl = `/products/search/?q=${encodeURIComponent(query)}`;

        fetch(searchUrl, {
            signal: currentAbortController.signal,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        })
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        })
        .then(data => {
            if (loader) loader.classList.remove('is-active');
            renderSearchResults(data);
        })
        .catch(err => {
            if (err.name === 'AbortError') return;
            if (loader) loader.classList.remove('is-active');
            console.error('Spotlight search error:', err);
        });
    };

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            executeSearch(input.value);
        }, debounceDelay);
    });

    // -------------------------------------------------------------------------
    // Render Results
    // -------------------------------------------------------------------------
    const renderSearchResults = (data) => {
        activeCardIndex = -1;
        const results = data.results || [];
        const isFeatured = !!data.is_featured_curation;

        if (results.length === 0) {
            // Empty state
            resultsList.innerHTML = '';
            resultsList.style.display = 'none';
            if (emptyState) emptyState.style.display = 'flex';
            if (resultsCount) {
                resultsCount.textContent = 'No Fragrances Found';
            }
            return;
        }

        // Has results
        if (emptyState) emptyState.style.display = 'none';
        resultsList.style.display = 'flex';

        if (resultsCount) {
            if (isFeatured) {
                resultsCount.textContent = 'Featured Curations';
            } else {
                resultsCount.textContent = `${data.count} Fragrance${data.count === 1 ? '' : 's'} Found`;
            }
        }

        let html = '';
        results.forEach((item, index) => {
            const originalPriceHtml = item.original_price
                ? `<span class="spotlight-card-orig-price">${item.original_price}</span>`
                : '';

            const ratingHtml = item.rating
                ? `<span class="spotlight-card-rating" aria-label="${item.rating} out of 5 stars">
                       <span class="spotlight-card-rating-star">★</span> ${item.rating}
                   </span>`
                : '';

            html += `
                <a href="${item.detail_url}"
                   class="spotlight-card"
                   data-index="${index}"
                   role="option"
                   aria-selected="false"
                   style="--item-idx: ${index};">
                    <div class="spotlight-card-thumb-wrap">
                        <img src="${item.image}" alt="${item.name}" class="spotlight-card-thumb" loading="lazy">
                    </div>
                    <div class="spotlight-card-info">
                        <div class="spotlight-card-meta">
                            <span class="spotlight-card-collection">${item.collection}</span>
                            ${ratingHtml}
                        </div>
                        <h4 class="spotlight-card-name">${item.name}</h4>
                        <p class="spotlight-card-note">${item.short_note}</p>
                    </div>
                    <div class="spotlight-card-aside">
                        <div class="spotlight-card-pricing">
                            <span class="spotlight-card-price">${item.price}</span>
                            ${originalPriceHtml}
                        </div>
                        <div class="spotlight-card-arrow" aria-hidden="true">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="5" y1="12" x2="19" y2="12"></line>
                                <polyline points="12 5 19 12 12 19"></polyline>
                            </svg>
                        </div>
                    </div>
                </a>
            `;
        });

        resultsList.innerHTML = html;

        // Re-attach empty state pill click handlers if needed
        const newEmptyPills = emptyState ? emptyState.querySelectorAll('.spotlight-empty-pill') : [];
        newEmptyPills.forEach(pill => {
            pill.onclick = () => {
                const query = pill.getAttribute('data-query');
                input.value = query;
                if (clearBtn) clearBtn.style.display = 'inline-flex';
                input.focus();
                executeSearch(query);
            };
        });
    };

    // -------------------------------------------------------------------------
    // Keyboard Navigation & Shortcuts (Spotlight Experience)
    // -------------------------------------------------------------------------
    const updateActiveCard = (cards, newIndex) => {
        cards.forEach((card, i) => {
            if (i === newIndex) {
                card.classList.add('is-active');
                card.setAttribute('aria-selected', 'true');
                card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                card.classList.remove('is-active');
                card.setAttribute('aria-selected', 'false');
            }
        });
        activeCardIndex = newIndex;
    };

    window.addEventListener('keydown', (e) => {
        // Global Shortcut: Cmd+K (Mac) or Ctrl+K (Windows/Linux)
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            if (overlay.classList.contains('is-open')) {
                closeSpotlight();
            } else {
                openSpotlight();
            }
            return;
        }

        // Overlay is open
        if (!overlay.classList.contains('is-open')) return;

        // ESC closes
        if (e.key === 'Escape') {
            e.preventDefault();
            closeSpotlight();
            return;
        }

        const cards = resultsList.querySelectorAll('.spotlight-card');

        // Down arrow: Navigate down
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (!cards.length) return;
            const nextIndex = activeCardIndex + 1 < cards.length ? activeCardIndex + 1 : 0;
            updateActiveCard(cards, nextIndex);
            return;
        }

        // Up arrow: Navigate up
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (!cards.length) return;
            const prevIndex = activeCardIndex - 1 >= 0 ? activeCardIndex - 1 : cards.length - 1;
            updateActiveCard(cards, prevIndex);
            return;
        }

        // Enter: Navigate to active or first result
        if (e.key === 'Enter') {
            if (cards.length > 0) {
                e.preventDefault();
                const targetCard = activeCardIndex >= 0 ? cards[activeCardIndex] : cards[0];
                if (targetCard) {
                    window.location.href = targetCard.href;
                }
            }
            return;
        }

        // Focus Trap: Tab key
        if (e.key === 'Tab') {
            const focusable = modal.querySelectorAll(
                'input, button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
            );
            if (!focusable.length) return;

            const firstElement = focusable[0];
            const lastElement = focusable[focusable.length - 1];

            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        }
    });
});
