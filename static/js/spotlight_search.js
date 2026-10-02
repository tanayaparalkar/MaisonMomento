/**
 * Maison Moménto — Apple Spotlight Search Experience
 * Live AJAX multi-entity search across Products, Collections, and Pages.
 * Keyboard navigation (↑/↓/↵/ESC/Cmd+K/Ctrl+K and "/"), recent searches in localStorage,
 * focus trap, smooth animations, and luxury aesthetics.
 */
(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", () => {
        const overlay = document.getElementById("spotlight-search-overlay");
        if (!overlay) return;

        const backdrop = document.getElementById("spotlight-backdrop");
        const modal = document.getElementById("spotlight-modal");
        const input = document.getElementById("spotlight-input");
        const loader = document.getElementById("spotlight-loader");
        const clearBtn = document.getElementById("spotlight-clear-btn");
        const closeBtn = document.getElementById("spotlight-close-btn");
        const resultsList = document.getElementById("spotlight-results-list");
        const resultsCount = document.getElementById("spotlight-results-count");
        const emptyState = document.getElementById("spotlight-empty-state");
        const quickTagsContainer = document.getElementById("spotlight-quick-tags");

        const searchTriggers = document.querySelectorAll(
            "#spotlight-search-trigger, .sf-search-trigger, [aria-label='Search']"
        );

        let currentAbortController = null;
        let activeCardIndex = -1;
        let lastActiveElement = null;
        let debounceTimer = null;
        const debounceDelay = 180;

        // LocalStorage Recent Searches Helper
        const STORAGE_KEY = "mm_recent_searches";
        const getRecentSearches = () => {
            try {
                const stored = localStorage.getItem(STORAGE_KEY);
                return stored ? JSON.parse(stored) : [];
            } catch (e) {
                return [];
            }
        };

        const saveRecentSearch = (query) => {
            const q = (query || "").trim();
            if (!q) return;
            try {
                let recents = getRecentSearches();
                recents = recents.filter((item) => item.toLowerCase() !== q.toLowerCase());
                recents.unshift(q);
                if (recents.length > 6) recents = recents.slice(0, 6);
                localStorage.setItem(STORAGE_KEY, JSON.stringify(recents));
            } catch (e) {}
        };

        const clearRecentSearches = () => {
            try {
                localStorage.removeItem(STORAGE_KEY);
            } catch (e) {}
        };

        // Icons
        const icons = {
            bottle: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>`,
            layers: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>`,
            compass: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>`,
            message: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`,
            sparkle: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>`,
            clock: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`,
        };

        // ---------------------------------------------------------------------
        // Open & Close Handlers
        // ---------------------------------------------------------------------
        const openSpotlight = () => {
            lastActiveElement = document.activeElement;
            overlay.classList.add("is-open");
            overlay.setAttribute("aria-hidden", "false");
            document.body.classList.add("spotlight-open");

            searchTriggers.forEach((btn) => btn.setAttribute("aria-expanded", "true"));

            setTimeout(() => {
                input.focus();
                if (input.value) {
                    input.select();
                }
            }, 60);

            // Execute search or load empty state
            executeSearch(input.value);
        };

        const closeSpotlight = () => {
            overlay.classList.remove("is-open");
            overlay.setAttribute("aria-hidden", "true");
            document.body.classList.remove("spotlight-open");

            searchTriggers.forEach((btn) => btn.setAttribute("aria-expanded", "false"));

            if (lastActiveElement && typeof lastActiveElement.focus === "function") {
                lastActiveElement.focus();
            }
        };

        searchTriggers.forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                openSpotlight();
            });
        });

        backdrop.addEventListener("click", closeSpotlight);

        if (closeBtn) {
            closeBtn.addEventListener("click", (e) => {
                e.preventDefault();
                closeSpotlight();
            });
        }

        if (clearBtn) {
            clearBtn.addEventListener("click", () => {
                input.value = "";
                clearBtn.style.display = "none";
                input.focus();
                executeSearch("");
            });
        }

        // Quick Tag Pills
        document.querySelectorAll(".spotlight-tag-pill").forEach((pill) => {
            pill.addEventListener("click", () => {
                const query = pill.getAttribute("data-query") || pill.textContent.trim();
                input.value = query;
                if (clearBtn) clearBtn.style.display = "inline-flex";
                input.focus();
                executeSearch(query);
            });
        });

        // ---------------------------------------------------------------------
        // AJAX Live Search
        // ---------------------------------------------------------------------
        const executeSearch = (rawQuery) => {
            const query = (rawQuery || "").trim();

            if (clearBtn) {
                clearBtn.style.display = rawQuery.length > 0 ? "inline-flex" : "none";
            }

            if (currentAbortController) {
                currentAbortController.abort();
            }
            currentAbortController = new AbortController();

            if (loader) loader.classList.add("is-active");

            const searchUrl = `/products/search/?q=${encodeURIComponent(query)}`;

            fetch(searchUrl, {
                signal: currentAbortController.signal,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    Accept: "application/json",
                },
            })
                .then((res) => {
                    if (!res.ok) throw new Error(`HTTP ${res.status}`);
                    return res.json();
                })
                .then((data) => {
                    if (loader) loader.classList.remove("is-active");
                    renderSearchResults(data, query);
                })
                .catch((err) => {
                    if (err.name === "AbortError") return;
                    if (loader) loader.classList.remove("is-active");
                    console.error("Spotlight search error:", err);
                });
        };

        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                executeSearch(input.value);
            }, debounceDelay);
        });

        // ---------------------------------------------------------------------
        // Render Grouped Search Results & Empty State
        // ---------------------------------------------------------------------
        const renderSearchResults = (data, currentQuery) => {
            activeCardIndex = -1;

            // --- 1. EMPTY STATE (Nothing typed) ---
            if (data.is_empty_state || !currentQuery) {
                if (emptyState) emptyState.style.display = "none";
                resultsList.style.display = "flex";
                if (resultsCount) resultsCount.textContent = "Discover Maison Moménto";

                let html = "";

                // A. Recent Searches (from localStorage)
                const recents = getRecentSearches();
                if (recents.length > 0) {
                    html += `
                        <div class="spotlight-recent-searches-box">
                            <div class="spotlight-recent-header">
                                <span>Recent Searches</span>
                                <button type="button" class="spotlight-clear-recent-btn" id="spotlight-clear-recent">Clear</button>
                            </div>
                            <div class="spotlight-recent-pills">
                                ${recents
                                    .map(
                                        (term) => `
                                    <button type="button" class="spotlight-recent-pill" data-query="${term}">
                                        ${icons.clock} <span>${term}</span>
                                    </button>
                                `
                                    )
                                    .join("")}
                            </div>
                        </div>
                    `;
                }

                // B. Collections
                const collections = data.collections || [];
                if (collections.length > 0) {
                    html += `
                        <div class="spotlight-section-block">
                            <div class="spotlight-section-heading">Collections &amp; Olfactory Families</div>
                            <div class="spotlight-recent-pills" style="margin-bottom: 8px;">
                                ${collections
                                    .map(
                                        (c) => `
                                    <a href="${c.detail_url}" class="spotlight-recent-pill spotlight-nav-link">
                                        ${icons.layers} <strong>${c.name}</strong> <span style="opacity: 0.6; font-size: 10px;">(${c.category})</span>
                                    </a>
                                `
                                    )
                                    .join("")}
                            </div>
                        </div>
                    `;
                }

                // C. Newest Fragrances
                const newest = data.newest_fragrances || [];
                if (newest.length > 0) {
                    html += `
                        <div class="spotlight-section-block">
                            <div class="spotlight-section-heading">Featured &amp; Newest Fragrances</div>
                    `;
                    newest.forEach((item, index) => {
                        html += `
                            <a href="${item.detail_url}" class="spotlight-card spotlight-nav-link" data-index="${index}" role="option" aria-selected="false">
                                <div class="spotlight-card-thumb-wrap">
                                    <img src="${item.image}" alt="${item.name}" class="spotlight-card-thumb" loading="lazy">
                                </div>
                                <div class="spotlight-card-info">
                                    <div class="spotlight-card-meta">
                                        <span class="spotlight-card-collection">${item.category}</span>
                                        ${item.rating ? `<span class="spotlight-card-rating">★ ${item.rating}</span>` : ""}
                                    </div>
                                    <h4 class="spotlight-card-name">${item.name}</h4>
                                    <p class="spotlight-card-note">${item.short_note}</p>
                                </div>
                                <div class="spotlight-card-aside">
                                    <div class="spotlight-card-pricing">
                                        <span class="spotlight-card-price">${item.price}</span>
                                    </div>
                                    <div class="spotlight-card-arrow" aria-hidden="true">&rarr;</div>
                                </div>
                            </a>
                        `;
                    });
                    html += `</div>`;
                }

                resultsList.innerHTML = html;

                // Attach recent searches clear button
                const clearRecentBtn = document.getElementById("spotlight-clear-recent");
                if (clearRecentBtn) {
                    clearRecentBtn.onclick = () => {
                        clearRecentSearches();
                        executeSearch("");
                    };
                }

                // Attach recent pills search
                resultsList.querySelectorAll(".spotlight-recent-pill[data-query]").forEach((pill) => {
                    pill.onclick = () => {
                        const term = pill.getAttribute("data-query");
                        input.value = term;
                        input.focus();
                        executeSearch(term);
                    };
                });

                return;
            }

            // --- 2. LIVE QUERY RESULTS GROUPED INTO SECTIONS ---
            const products = data.products || [];
            const collections = data.collections || [];
            const pages = data.pages || [];
            const totalCount = (products.length) + (collections.length) + (pages.length);

            if (totalCount === 0) {
                // NO RESULTS
                resultsList.innerHTML = "";
                resultsList.style.display = "none";
                if (emptyState) emptyState.style.display = "flex";
                if (resultsCount) resultsCount.textContent = "No Results";
                return;
            }

            // Has results
            if (emptyState) emptyState.style.display = "none";
            resultsList.style.display = "flex";
            if (resultsCount) {
                resultsCount.textContent = `${totalCount} Result${totalCount === 1 ? "" : "s"} across Maison Moménto`;
            }

            let html = "";
            let overallIndex = 0;

            // SECTION A: Products
            if (products.length > 0) {
                html += `
                    <div class="spotlight-section-block">
                        <div class="spotlight-section-heading">
                            <span>Products (${products.length})</span>
                            <span style="font-weight: normal; opacity: 0.7;">Fine Fragrances</span>
                        </div>
                `;
                products.forEach((item) => {
                    html += `
                        <a href="${item.detail_url}" class="spotlight-card spotlight-nav-link" data-index="${overallIndex++}" data-term="${currentQuery}" role="option" aria-selected="false">
                            <div class="spotlight-card-thumb-wrap">
                                <img src="${item.image}" alt="${item.name}" class="spotlight-card-thumb" loading="lazy">
                            </div>
                            <div class="spotlight-card-info">
                                <div class="spotlight-card-meta">
                                    <span class="spotlight-card-collection">${item.category}</span>
                                    ${item.rating ? `<span class="spotlight-card-rating">★ ${item.rating}</span>` : ""}
                                </div>
                                <h4 class="spotlight-card-name">${item.name}</h4>
                                <p class="spotlight-card-note">${item.short_note}</p>
                            </div>
                            <div class="spotlight-card-aside">
                                <div class="spotlight-card-pricing">
                                    <span class="spotlight-card-price">${item.price}</span>
                                </div>
                                <div class="spotlight-card-arrow" aria-hidden="true">&rarr;</div>
                            </div>
                        </a>
                    `;
                });
                html += `</div>`;
            }

            // SECTION B: Collections
            if (collections.length > 0) {
                html += `
                    <div class="spotlight-section-block">
                        <div class="spotlight-section-heading">
                            <span>Collections (${collections.length})</span>
                            <span style="font-weight: normal; opacity: 0.7;">Olfactory Families</span>
                        </div>
                `;
                collections.forEach((c) => {
                    html += `
                        <a href="${c.detail_url}" class="spotlight-generic-card spotlight-nav-link" data-index="${overallIndex++}" data-term="${currentQuery}" role="option" aria-selected="false">
                            <div class="spotlight-generic-card-left">
                                <span class="spotlight-generic-icon">${icons.layers}</span>
                                <div class="spotlight-generic-info">
                                    <h4 class="spotlight-generic-title">${c.name}</h4>
                                    <span class="spotlight-generic-desc">${c.category}</span>
                                </div>
                            </div>
                            <div class="spotlight-card-arrow">&rarr;</div>
                        </a>
                    `;
                });
                html += `</div>`;
            }

            // SECTION C: Static Pages
            if (pages.length > 0) {
                html += `
                    <div class="spotlight-section-block">
                        <div class="spotlight-section-heading">
                            <span>Pages (${pages.length})</span>
                            <span style="font-weight: normal; opacity: 0.7;">Maison Destinations</span>
                        </div>
                `;
                pages.forEach((p) => {
                    const iconSvg = icons[p.icon] || icons.compass;
                    html += `
                        <a href="${p.detail_url}" class="spotlight-generic-card spotlight-nav-link" data-index="${overallIndex++}" data-term="${currentQuery}" role="option" aria-selected="false">
                            <div class="spotlight-generic-card-left">
                                <span class="spotlight-generic-icon">${iconSvg}</span>
                                <div class="spotlight-generic-info">
                                    <h4 class="spotlight-generic-title">${p.name}</h4>
                                    <span class="spotlight-generic-desc">${p.category}</span>
                                </div>
                            </div>
                            <div class="spotlight-card-arrow">&rarr;</div>
                        </a>
                    `;
                });
                html += `</div>`;
            }

            resultsList.innerHTML = html;

            // Track recent search on click
            resultsList.querySelectorAll(".spotlight-nav-link").forEach((link) => {
                link.addEventListener("click", () => {
                    saveRecentSearch(currentQuery);
                });
            });
        };

        // ---------------------------------------------------------------------
        // Keyboard Navigation (↑/↓/↵/ESC/Focus Trap)
        // ---------------------------------------------------------------------
        const updateActiveCard = (cards, newIndex) => {
            cards.forEach((card, i) => {
                if (i === newIndex) {
                    card.classList.add("is-active");
                    card.setAttribute("aria-selected", "true");
                    card.scrollIntoView({ block: "nearest", behavior: "smooth" });
                } else {
                    card.classList.remove("is-active");
                    card.setAttribute("aria-selected", "false");
                }
            });
            activeCardIndex = newIndex;
        };

        window.addEventListener("keydown", (e) => {
            // Global Shortcut: ⌘K (Mac) or Ctrl+K (Windows/Linux)
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
                e.preventDefault();
                if (overlay.classList.contains("is-open")) {
                    closeSpotlight();
                } else {
                    openSpotlight();
                }
                return;
            }

            // Global Slash ("/") shortcut when not typing in an input or textarea
            if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
                e.preventDefault();
                openSpotlight();
                return;
            }

            // Only proceed if overlay is open
            if (!overlay.classList.contains("is-open")) return;

            // ESC closes
            if (e.key === "Escape") {
                e.preventDefault();
                closeSpotlight();
                return;
            }

            const cards = resultsList.querySelectorAll(".spotlight-card, .spotlight-generic-card");

            // Down arrow: Navigate down
            if (e.key === "ArrowDown") {
                e.preventDefault();
                if (!cards.length) return;
                const nextIndex = activeCardIndex + 1 < cards.length ? activeCardIndex + 1 : 0;
                updateActiveCard(cards, nextIndex);
                return;
            }

            // Up arrow: Navigate up
            if (e.key === "ArrowUp") {
                e.preventDefault();
                if (!cards.length) return;
                const prevIndex = activeCardIndex - 1 >= 0 ? activeCardIndex - 1 : cards.length - 1;
                updateActiveCard(cards, prevIndex);
                return;
            }

            // Enter: Navigate to active or first result
            if (e.key === "Enter") {
                if (cards.length > 0) {
                    e.preventDefault();
                    const targetCard = activeCardIndex >= 0 ? cards[activeCardIndex] : cards[0];
                    if (targetCard) {
                        saveRecentSearch(input.value);
                        window.location.href = targetCard.href;
                    }
                }
                return;
            }

            // Focus Trap: Tab key
            if (e.key === "Tab") {
                const focusable = modal.querySelectorAll(
                    "input, button:not([disabled]), [href], [tabindex]:not([tabindex='-1'])"
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
})();
