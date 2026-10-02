document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const selectors = {
        salesChart: "#salesChart",
        analyticsChart: "#analyticsChart",
        pieChart: "#pieChart",
        productDrawer: ".product-drawer",
        drawerOverlay: ".drawer-overlay",
        drawerClose: ".drawer-close",
        productRows: ".product-row",
        addModal: "#addModal",
        openModal: "#openModal",
        closeModal: ".close-modal, .modal-close",
        dropdownButton: ".dropbtn",
        dropdown: ".dropdown",
        filters: ".filter",
        counters: "[data-counter]",
        recommendationStars: ".recommendation-stars",
    };

    const colors = {
        navy: "#0D2538",
        navySoft: "rgba(13, 37, 56, 0.14)",
        navyFade: "rgba(13, 37, 56, 0)",
        forest: "#184C45",
        forestSoft: "rgba(24, 76, 69, 0.13)",
        burgundy: "#701B25",
        burgundySoft: "rgba(112, 27, 37, 0.12)",
        charcoal: "#463833",
        muted: "#817C78",
        grid: "rgba(230, 230, 227, 0.95)",
        white: "#FFFFFF",
    };

    const drawer = document.querySelector(selectors.productDrawer);
    const drawerOverlay = document.querySelector(selectors.drawerOverlay);
    const drawerCloseButton = document.querySelector(selectors.drawerClose);
    const addModal = document.querySelector(selectors.addModal);
    const openModalButton = document.querySelector(selectors.openModal);

    /* =========================================================================
       SHARED CHART HELPERS
       ========================================================================= */

    const getChartHeight = (canvas) => {
        return canvas.parentElement ? canvas.parentElement.clientHeight : 350;
    };

    const createAreaGradient = (context, height, topColor, middleColor, fadeColor) => {
        const gradient = context.createLinearGradient(0, 0, 0, height);

        gradient.addColorStop(0, topColor);
        gradient.addColorStop(0.48, middleColor);
        gradient.addColorStop(1, fadeColor);

        return gradient;
    };

    const createPremiumTooltip = (accentColor, valueFormatter) => {
        return {
            enabled: true,
            displayColors: false,
            backgroundColor: colors.white,
            titleColor: colors.charcoal,
            bodyColor: colors.charcoal,
            borderColor: "rgba(13, 37, 56, 0.10)",
            borderWidth: 1,
            cornerRadius: 9,
            caretSize: 5,
            caretPadding: 9,
            padding: {
                top: 10,
                right: 12,
                bottom: 10,
                left: 12,
            },

            titleFont: {
                family: "Inter",
                size: 10,
                weight: "600",
            },

            bodyFont: {
                family: "Cormorant Garamond",
                size: 19,
                weight: "600",
            },

            titleMarginBottom: 4,

            animation: {
                duration: 160,
                easing: "easeOutQuart",
            },

            callbacks: {
                label(context) {
                    return valueFormatter(context);
                },
            },

            external(context) {
                const tooltipElement = context.tooltip;

                if (!tooltipElement || !tooltipElement.opacity) {
                    return;
                }

                const tooltipCanvas = context.chart.canvas;
                tooltipCanvas.style.cursor = tooltipElement.dataPoints?.length
                    ? "pointer"
                    : "default";
            },
        };
    };

    const createGrowthLineAnimation = () => {
        const totalDuration = 2000;
        const delayBetweenPoints = totalDuration / 6;

        return {
            x: {
                type: "number",
                easing: "linear",
                duration: delayBetweenPoints,
                from: Number.NaN,
                delay(context) {
                    if (context.type !== "data" || context.xStarted) {
                        return 0;
                    }
                    context.xStarted = true;
                    return context.index * delayBetweenPoints;
                },
            },
            y: {
                type: "number",
                easing: "linear",
                duration: delayBetweenPoints,
                from: (context) => {
                    if (context.index === 0) {
                        return context.chart.scales.y.getPixelForValue(0);
                    }
                    const meta = context.chart.getDatasetMeta(context.datasetIndex);
                    const prev = meta.data[context.index - 1];
                    return prev ? prev.getProps(["y"], true).y : 0;
                },
                delay(context) {
                    if (context.type !== "data" || context.yStarted) {
                        return 0;
                    }
                    context.yStarted = true;
                    return context.index * delayBetweenPoints;
                },
            },
        };
    };

    const createLineChartOptions = (valueFormatter) => {
        return {
            responsive: true,
            maintainAspectRatio: false,

            interaction: {
                intersect: false,
                mode: "index",
            },

            animation: {
                duration: 2000,
                easing: "easeOutCubic",
                delay: 0,
            },

            animations: createGrowthLineAnimation(),

            plugins: {
                legend: {
                    display: false,
                },

                tooltip: createPremiumTooltip(
                    colors.navy,
                    valueFormatter
                ),
            },

            elements: {
                line: {
                    borderJoinStyle: "round",
                    capBezierPoints: true,
                },

                point: {
                    hoverRadius: 4.5,
                    hoverBorderWidth: 2,
                },
            },

            scales: {
                x: {
                    grid: {
                        display: false,
                    },

                    border: {
                        display: false,
                    },

                    ticks: {
                        color: colors.muted,
                        font: {
                            family: "Inter",
                            size: 10,
                            weight: "500",
                        },
                        padding: 13,
                        maxRotation: 0,
                    },
                },

                y: {
                    beginAtZero: true,

                    border: {
                        display: false,
                    },

                    ticks: {
                        display: false,
                    },

                    grid: {
                        color: colors.grid,
                        drawTicks: false,
                        lineWidth: 1,
                    },
                },
            },
        };
    };

    const createLineDataset = (data, accentColor, areaGradient) => {
        return {
            label: "Revenue",
            data,

            borderColor: accentColor,
            backgroundColor: areaGradient,
            fill: true,

            borderWidth: 2.15,
            tension: 0.46,

            pointRadius: 2.25,
            pointHoverRadius: 4.5,
            pointHitRadius: 18,

            pointBackgroundColor: colors.white,
            pointBorderColor: accentColor,
            pointBorderWidth: 1.5,
            pointHoverBackgroundColor: accentColor,
            pointHoverBorderColor: colors.white,
        };
    };

    /* =========================================================================
       DASHBOARD SALES CHART
       ========================================================================= */

    const salesCanvas = document.querySelector(selectors.salesChart);

    if (salesCanvas && typeof Chart !== "undefined") {
        const context = salesCanvas.getContext("2d");
        const areaGradient = createAreaGradient(
            context,
            getChartHeight(salesCanvas),
            "rgba(13, 37, 56, 0.13)",
            "rgba(13, 37, 56, 0.045)",
            colors.navyFade
        );

        new Chart(context, {
            type: "line",

            data: {
                labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],

                datasets: [
                    createLineDataset(
                        [2.8, 3.6, 4.5, 5.1, 6.8, 8.4],
                        colors.navy,
                        areaGradient
                    ),
                ],
            },

            options: createLineChartOptions(
                (context) => `₹${context.parsed.y.toFixed(1)}L`
            ),
        });
    }

    /* =========================================================================
       ANALYTICS REVENUE TREND CHART
       ========================================================================= */

    const analyticsCanvas = document.querySelector(selectors.analyticsChart);

    if (analyticsCanvas && typeof Chart !== "undefined") {
        const context = analyticsCanvas.getContext("2d");
        const areaGradient = createAreaGradient(
            context,
            getChartHeight(analyticsCanvas),
            "rgba(24, 76, 69, 0.14)",
            "rgba(24, 76, 69, 0.045)",
            "rgba(24, 76, 69, 0)"
        );

        const chartLabels = (window.INSIGHTS_DATA && window.INSIGHTS_DATA.labels && window.INSIGHTS_DATA.labels.length) 
            ? window.INSIGHTS_DATA.labels 
            : ["Jan", "Feb", "Mar", "Apr", "May", "Jun"];

        const chartRevenues = (window.INSIGHTS_DATA && window.INSIGHTS_DATA.revenues && window.INSIGHTS_DATA.revenues.length) 
            ? window.INSIGHTS_DATA.revenues 
            : [2.4, 2.8, 3.6, 4.2, 5.4, 6.1];

        new Chart(context, {
            type: "line",
            data: {
                labels: chartLabels,
                datasets: [
                    createLineDataset(
                        chartRevenues,
                        colors.forest,
                        areaGradient
                    ),
                ],
            },
            options: createLineChartOptions(
                (context) => `₹${context.parsed.y.toFixed(1)}L`
            ),
        });
    }

    /* =========================================================================
       ANALYTICS SALES DISTRIBUTION CHART
       ========================================================================= */

    const pieCanvas = document.querySelector(selectors.pieChart);

    if (pieCanvas && typeof Chart !== "undefined") {
        const context = pieCanvas.getContext("2d");

        const pieLabels = (window.INSIGHTS_DATA && window.INSIGHTS_DATA.categoryLabels && window.INSIGHTS_DATA.categoryLabels.length)
            ? window.INSIGHTS_DATA.categoryLabels
            : ["Woody Collection", "Oud Collection", "Musky Collection", "Fresh Collection"];

        const pieData = (window.INSIGHTS_DATA && window.INSIGHTS_DATA.categoryPercentages && window.INSIGHTS_DATA.categoryPercentages.length)
            ? window.INSIGHTS_DATA.categoryPercentages
            : [38, 27, 21, 14];

        new Chart(context, {
            type: "doughnut",
            data: {
                labels: pieLabels,
                datasets: [
                    {
                        data: pieData,
                        backgroundColor: [
                            colors.navy,
                            colors.forest,
                            colors.burgundy,
                            "#C5A059",
                            "#817C78",
                            "#5A3825",
                        ],
                        borderColor: colors.white,
                        borderWidth: 3,
                        borderRadius: 3,
                        spacing: 2,
                        hoverOffset: 15,
                    },
                ],
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "74%",
                rotation: -90,
                circumference: 360,

                animation: {
                    animateRotate: true,
                    animateScale: false,
                    duration: 1800,
                    easing: "easeOutQuart",
                    delay: 0,
                },

                plugins: {
                    legend: {
                        position: "bottom",
                        align: "center",
                        labels: {
                            boxWidth: 8,
                            boxHeight: 8,
                            borderRadius: 4,
                            padding: 14,
                            color: colors.muted,
                            font: {
                                family: "Inter",
                                size: 11,
                                weight: "500",
                            },
                            usePointStyle: true,
                            pointStyle: "circle",
                        },
                    },
                    tooltip: createPremiumTooltip(
                        colors.navy,
                        (context) => `${context.parsed}% of total sales`
                    ),
                },

                elements: {
                    arc: {
                        borderJoinStyle: "round",
                    },
                },
            },
        });
    }

    /* =========================================================================
       CASINO / SLOT-MACHINE ROLLING COUNTER ANIMATION
       ========================================================================= */

    const animateCasinoCounter = (element) => {
        const rawTarget = element.dataset.counter;
        if (rawTarget === undefined || rawTarget === null || rawTarget === "") {
            return;
        }

        const target = Number(rawTarget);
        if (Number.isNaN(target)) {
            return;
        }

        const prefix = element.dataset.prefix || "";
        const suffix = element.dataset.suffix || "";
        const displayValue = element.dataset.displayValue;
        const isDecimal = !Number.isInteger(target) || Boolean(displayValue);

        // Target string formatted for final lock-in
        const formatTargetValue = (val) => {
            if (displayValue && suffix === "L") {
                return `${prefix}${displayValue}${suffix}`;
            }
            if (isDecimal) {
                return `${prefix}${val.toFixed(1)}${suffix}`;
            }
            return `${prefix}${Math.round(val).toLocaleString("en-IN")}${suffix}`;
        };

        const finalFormatted = formatTargetValue(target);

        // Casino roll duration
        const duration = target > 500 ? 1600 : 1200;
        const startTime = performance.now();

        // Helper to generate rolling reel numbers of matching scale
        const getRandomReelNumber = () => {
            if (target === 0) return 0;
            if (target < 10) return Math.floor(Math.random() * 10);
            if (target < 100) return Math.floor(Math.random() * 90 + 10);
            const digits = Math.max(2, Math.floor(Math.log10(target)) + 1);
            const min = Math.pow(10, digits - 1);
            const max = Math.pow(10, digits) - 1;
            return Math.floor(Math.random() * (max - min) + min);
        };

        let lastFrameTime = 0;

        const updateReels = (currentTime) => {
            const elapsed = Math.min((currentTime - startTime) / duration, 1);

            // Phase 1: Rapid casino spinning reels (0% to 58% of duration)
            if (elapsed < 0.58) {
                // Update reel characters rapidly at ~30ms intervals
                if (currentTime - lastFrameTime > 30) {
                    lastFrameTime = currentTime;
                    if (target === 0) {
                        element.textContent = `${prefix}0${suffix}`;
                    } else if (displayValue && suffix === "L") {
                        element.textContent = `${prefix}${(Math.random() * 15).toFixed(1)}${suffix}`;
                    } else if (isDecimal) {
                        element.textContent = `${prefix}${(Math.random() * target).toFixed(1)}${suffix}`;
                    } else {
                        const randomNum = getRandomReelNumber();
                        element.textContent = `${prefix}${randomNum.toLocaleString("en-IN")}${suffix}`;
                    }
                }
                window.requestAnimationFrame(updateReels);
                return;
            }

            // Phase 2: Mechanical deceleration into the target jackpot number (58% to 100%)
            const decelProgress = (elapsed - 0.58) / 0.42;
            // Smooth ease-out cubic curve
            const ease = 1 - Math.pow(1 - decelProgress, 3);
            const currentVal = target * (0.58 + 0.42 * ease);

            if (elapsed < 1) {
                if (displayValue && suffix === "L") {
                    const interpolatedDisplay = (Number(displayValue) * (0.58 + 0.42 * ease)).toFixed(1);
                    element.textContent = `${prefix}${interpolatedDisplay}${suffix}`;
                } else if (isDecimal) {
                    element.textContent = `${prefix}${currentVal.toFixed(1)}${suffix}`;
                } else {
                    element.textContent = `${prefix}${Math.round(currentVal).toLocaleString("en-IN")}${suffix}`;
                }
                window.requestAnimationFrame(updateReels);
            } else {
                // Phase 3: Final lock-in and celebratory jackpot bounce
                element.textContent = finalFormatted;
                element.classList.remove("casino-spin");
                element.classList.add("casino-lock");
            }
        };

        element.classList.add("casino-spin");
        window.requestAnimationFrame(updateReels);
    };

    // Stagger all counters across the dashboard
    document.querySelectorAll(selectors.counters).forEach((counter, index) => {
        window.setTimeout(() => {
            animateCasinoCounter(counter);
        }, 120 + index * 90);
    });

    /* =========================================================================
       RECOMMENDATION STAR ANIMATION
       ========================================================================= */

    document.querySelectorAll(selectors.recommendationStars).forEach(
        (starElement, rowIndex) => {
            const totalStars = Number(starElement.dataset.stars);

            if (Number.isNaN(totalStars) || totalStars < 1) {
                return;
            }

            starElement.textContent = "☆☆☆☆☆";

            window.setTimeout(() => {
                let currentStar = 0;

                const addStar = () => {
                    currentStar += 1;

                    starElement.textContent =
                        "★".repeat(currentStar) +
                        "☆".repeat(Math.max(0, 5 - currentStar));

                    if (currentStar < totalStars) {
                        window.setTimeout(addStar, 115);
                    }
                };

                addStar();
            }, 420 + rowIndex * 170);
        }
    );

    /* =========================================================================
       FILTER ACTIVE STATE
       ========================================================================= */

    document.querySelectorAll(selectors.filters).forEach((filterButton) => {
        filterButton.addEventListener("click", () => {
            const filterContainer = filterButton.parentElement;

            if (!filterContainer) {
                return;
            }

            filterContainer.querySelectorAll(selectors.filters).forEach((button) => {
                button.classList.remove("active");
            });

            filterButton.classList.add("active");
        });
    });

    /* =========================================================================
       PRODUCT DRAWER
       ========================================================================= */

    const setDrawerState = (isOpen) => {
        if (!drawer || !drawerOverlay) {
            return;
        }

        drawer.classList.toggle("open", isOpen);
        drawerOverlay.classList.toggle("show", isOpen);

        drawer.setAttribute("aria-hidden", String(!isOpen));
        document.body.style.overflow = isOpen ? "hidden" : "";
    };

    const openDrawer = () => {
        setDrawerState(true);
    };

    const closeDrawer = () => {
        setDrawerState(false);
    };

    document.querySelectorAll(selectors.productRows).forEach((productRow) => {
        productRow.addEventListener("click", (event) => {
            const clickedButton = event.target.closest("button, a, input, select");

            if (clickedButton) {
                return;
            }

            openDrawer();
        });
    });

    if (drawerCloseButton) {
        drawerCloseButton.addEventListener("click", closeDrawer);
    }

    if (drawerOverlay) {
        drawerOverlay.addEventListener("click", closeDrawer);
    }

    /* =========================================================================
       ADD FRAGRANCE MODAL
       ========================================================================= */

    const setModalState = (isOpen) => {
        if (!addModal) {
            return;
        }

        addModal.classList.toggle("show", isOpen);
        addModal.setAttribute("aria-hidden", String(!isOpen));

        if (isOpen) {
            document.body.style.overflow = "hidden";

            const firstInput = addModal.querySelector(
                "input, select, textarea, button"
            );

            if (firstInput) {
                window.setTimeout(() => firstInput.focus(), 150);
            }
        } else if (!drawer || !drawer.classList.contains("open")) {
            document.body.style.overflow = "";
        }
    };

    const openModal = () => {
        setModalState(true);
    };

    const closeModal = () => {
        setModalState(false);
    };

    if (openModalButton && addModal) {
        openModalButton.addEventListener("click", openModal);
    }

    document.querySelectorAll(selectors.closeModal).forEach((button) => {
        button.addEventListener("click", closeModal);
    });

    if (addModal) {
        addModal.addEventListener("click", (event) => {
            if (event.target === addModal) {
                closeModal();
            }
        });
    }

    /* =========================================================================
       NAVIGATION DROPDOWN — ACCESSIBLE CLICK SUPPORT
       ========================================================================= */

    document.querySelectorAll(selectors.dropdownButton).forEach((button) => {
        button.addEventListener("click", () => {
            const dropdown = button.closest(selectors.dropdown);

            if (!dropdown) {
                return;
            }

            const isOpen = button.getAttribute("aria-expanded") === "true";

            document.querySelectorAll(selectors.dropdownButton).forEach(
                (otherButton) => {
                    otherButton.setAttribute("aria-expanded", "false");
                }
            );

            button.setAttribute("aria-expanded", String(!isOpen));
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(selectors.dropdown)) {
            document.querySelectorAll(selectors.dropdownButton).forEach(
                (button) => {
                    button.setAttribute("aria-expanded", "false");
                }
            );
        }
    });

    /* =========================================================================
       SLIDE-OVER PROFILE DRAWER
       ========================================================================= */

    const profileToggle = document.getElementById("profile-drawer-toggle");
    const profileDrawer = document.getElementById("profile-drawer");
    const profileBackdrop = document.getElementById("profile-drawer-backdrop");
    const profileCloseBtn = document.getElementById("profile-drawer-close");

    const setProfileDrawerState = (isOpen) => {
        if (!profileDrawer || !profileBackdrop) {
            return;
        }

        profileDrawer.classList.toggle("is-open", isOpen);
        profileBackdrop.classList.toggle("is-open", isOpen);

        profileDrawer.setAttribute("aria-hidden", String(!isOpen));
        document.body.style.overflow = isOpen ? "hidden" : "";

        if (profileToggle) {
            profileToggle.setAttribute("aria-expanded", String(isOpen));
        }

        if (isOpen) {
            // Focus the close button when opened for accessibility
            window.setTimeout(() => {
                if (profileCloseBtn) {
                    profileCloseBtn.focus();
                }
            }, 360);
        }
    };

    const openProfileDrawer = () => {
        setProfileDrawerState(true);
    };

    const closeProfileDrawer = () => {
        setProfileDrawerState(false);
    };

    const toggleProfileDrawer = () => {
        const isOpen =
            profileDrawer &&
            profileDrawer.classList.contains("is-open");

        setProfileDrawerState(!isOpen);
    };

    if (profileToggle) {
        profileToggle.addEventListener("click", toggleProfileDrawer);
    }

    if (profileCloseBtn) {
        profileCloseBtn.addEventListener("click", closeProfileDrawer);
    }

    if (profileBackdrop) {
        profileBackdrop.addEventListener("click", closeProfileDrawer);
    }

    // Focus trap: keep Tab inside the open drawer
    if (profileDrawer) {
        profileDrawer.addEventListener("keydown", (event) => {
            if (event.key !== "Tab") {
                return;
            }

            const focusable = profileDrawer.querySelectorAll(
                'a[href], button:not([disabled]), input:not([disabled]), textarea, select, [tabindex]:not([tabindex="-1"])'
            );

            if (!focusable.length) {
                return;
            }

            const first = focusable[0];
            const last = focusable[focusable.length - 1];

            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        });
    }

    /* =========================================================================
       ADMIN SEARCH NAVIGATION SHORTCUT & COMMAND PALETTE (Linear/Notion style)
       ========================================================================= */
    const searchInput = document.getElementById("global-search");
    const searchDropdown = document.getElementById("global-search-dropdown");
    const routesConfigEl = document.getElementById("dashboard-nav-routes");

    if (searchInput && searchDropdown && routesConfigEl) {
        let navRoutes = [];
        try {
            navRoutes = JSON.parse(routesConfigEl.textContent);
        } catch (e) {
            console.error("Failed to parse nav routes config:", e);
        }

        const routeIcons = {
            "Dashboard": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>`,
            "Products": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>`,
            "Categories": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>`,
            "Orders": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>`,
            "Vouchers": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>`,
            "Clients": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>`,
            "Recommendations": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>`,
            "Insights": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>`,
            "Stock & Inventory": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="21 8 21 21 3 21 3 8"></polyline><rect x="1" y="3" width="22" height="5"></rect><line x1="10" y1="12" x2="14" y2="12"></line></svg>`,
            "Reviews": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`,
            "Settings": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>`,
            "Contact Settings": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>`,
            "Admin Profile": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`,
            "Notifications": `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>`
        };

        const escapeHtml = (str) => {
            return (str || "").replace(/[&<>"']/g, (m) => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#039;"
            })[m]);
        };

        let selectedIndex = -1;
        let currentMatches = [];

        const closeSearchDropdown = () => {
            searchDropdown.style.display = "none";
            searchDropdown.innerHTML = "";
            selectedIndex = -1;
            currentMatches = [];
            searchInput.setAttribute("aria-expanded", "false");
        };

        const renderSuggestions = (matches, headerTitle = "Quick Jump") => {
            currentMatches = matches;
            selectedIndex = -1;

            if (!matches.length) {
                const queryEscaped = escapeHtml(searchInput.value.trim());
                searchDropdown.innerHTML = `
                    <div class="nav-search-header">Search Navigation</div>
                    <div class="nav-search-empty">
                        <div>No dashboard section matches "${queryEscaped}"</div>
                        <div class="nav-search-empty-tip">Products, orders, and clients have dedicated search boxes inside their sections.</div>
                    </div>
                    <div class="nav-search-footer">
                        <span><kbd>esc</kbd> close</span>
                    </div>
                `;
                searchDropdown.style.display = "block";
                searchInput.setAttribute("aria-expanded", "true");
                return;
            }

            let itemsHtml = "";
            matches.forEach((dest, idx) => {
                const iconSvg = routeIcons[dest.name] || `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="9 18 15 12 9 6"></polyline></svg>`;
                itemsHtml += `
                    <div class="nav-search-item" data-index="${idx}" data-url="${dest.url}" role="option" aria-selected="false">
                        <div class="nav-search-item-left">
                            <span class="nav-search-item-icon" aria-hidden="true">${iconSvg}</span>
                            <div class="nav-search-item-info">
                                <span class="nav-search-item-title">${dest.name}</span>
                                <span class="nav-search-item-category">${dest.category}</span>
                            </div>
                        </div>
                        <span class="nav-search-item-arrow">&rarr;</span>
                    </div>
                `;
            });

            searchDropdown.innerHTML = `
                <div class="nav-search-header">${headerTitle}</div>
                <div class="nav-search-list">${itemsHtml}</div>
                <div class="nav-search-footer">
                    <span><kbd>&uarr;</kbd><kbd>&darr;</kbd> navigate</span>
                    <span><kbd>&crarr;</kbd> jump</span>
                    <span><kbd>esc</kbd> close</span>
                </div>
            `;
            searchDropdown.style.display = "block";
            searchInput.setAttribute("aria-expanded", "true");

            // Attach click handler to each item
            searchDropdown.querySelectorAll(".nav-search-item").forEach((el) => {
                el.addEventListener("click", () => {
                    const url = el.getAttribute("data-url");
                    if (url) {
                        window.location.href = url;
                    }
                });
            });
        };

        const updateSelection = (newIndex) => {
            const items = searchDropdown.querySelectorAll(".nav-search-item");
            items.forEach((item, idx) => {
                if (idx === newIndex) {
                    item.classList.add("is-selected");
                    item.setAttribute("aria-selected", "true");
                    item.scrollIntoView({ block: "nearest" });
                } else {
                    item.classList.remove("is-selected");
                    item.setAttribute("aria-selected", "false");
                }
            });
            selectedIndex = newIndex;
        };

        const filterRoutes = (query) => {
            const q = query.trim().toLowerCase();
            if (!q) {
                renderSuggestions(navRoutes.slice(0, 7), "Quick Jump");
                return;
            }

            const matches = navRoutes.filter((dest) => {
                const nameMatch = dest.name.toLowerCase().includes(q);
                const categoryMatch = dest.category.toLowerCase().includes(q);
                const keywordMatch = dest.keywords && dest.keywords.some((kw) => kw.toLowerCase().includes(q));
                return nameMatch || categoryMatch || keywordMatch;
            });

            renderSuggestions(matches, "Matching Sections");
        };

        searchInput.addEventListener("input", () => {
            filterRoutes(searchInput.value);
        });

        searchInput.addEventListener("focus", () => {
            if (searchInput.value.trim()) {
                filterRoutes(searchInput.value);
            } else {
                renderSuggestions(navRoutes.slice(0, 7), "Quick Jump");
            }
        });

        searchInput.addEventListener("keydown", (e) => {
            if (searchDropdown.style.display === "none") {
                if (e.key === "Enter") {
                    e.preventDefault();
                    filterRoutes(searchInput.value);
                    if (currentMatches.length > 0) {
                        window.location.href = currentMatches[0].url;
                    }
                }
                return;
            }

            if (e.key === "ArrowDown") {
                e.preventDefault();
                if (!currentMatches.length) return;
                const next = selectedIndex + 1 < currentMatches.length ? selectedIndex + 1 : 0;
                updateSelection(next);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                if (!currentMatches.length) return;
                const prev = selectedIndex - 1 >= 0 ? selectedIndex - 1 : currentMatches.length - 1;
                updateSelection(prev);
            } else if (e.key === "Enter") {
                e.preventDefault();
                if (selectedIndex >= 0 && selectedIndex < currentMatches.length) {
                    window.location.href = currentMatches[selectedIndex].url;
                } else if (currentMatches.length > 0) {
                    window.location.href = currentMatches[0].url;
                }
            } else if (e.key === "Escape") {
                closeSearchDropdown();
                searchInput.blur();
            }
        });

        // Global Command Palette Shortcut: ⌘K or Ctrl+K or "/"
        document.addEventListener("keydown", (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
                if (searchInput.value.trim()) {
                    filterRoutes(searchInput.value);
                } else {
                    renderSuggestions(navRoutes.slice(0, 7), "Quick Jump");
                }
                return;
            }

            if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
                if (searchInput.value.trim()) {
                    filterRoutes(searchInput.value);
                } else {
                    renderSuggestions(navRoutes.slice(0, 7), "Quick Jump");
                }
                return;
            }
        });

        document.addEventListener("click", (e) => {
            if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
                closeSearchDropdown();
            }
        });
    }

    /* =========================================================================
       EXPORT DROPDOWN CONTROLS
       ========================================================================= */
    document.querySelectorAll(".export-dropdown-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const wrapper = btn.closest(".export-dropdown-wrapper");
            if (!wrapper) return;
            const isOpen = wrapper.classList.contains("is-open");

            // Close other open export dropdowns
            document.querySelectorAll(".export-dropdown-wrapper").forEach((w) => {
                w.classList.remove("is-open");
                const b = w.querySelector(".export-dropdown-btn");
                if (b) b.setAttribute("aria-expanded", "false");
            });

            if (!isOpen) {
                wrapper.classList.add("is-open");
                btn.setAttribute("aria-expanded", "true");
            }
        });
    });

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".export-dropdown-wrapper")) {
            document.querySelectorAll(".export-dropdown-wrapper").forEach((w) => {
                w.classList.remove("is-open");
                const b = w.querySelector(".export-dropdown-btn");
                if (b) b.setAttribute("aria-expanded", "false");
            });
        }
    });

    /* =========================================================================
       ESCAPE KEY — CLOSE OPEN INTERFACES
       ========================================================================= */

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        closeDrawer();
        closeModal();
        closeProfileDrawer();

        if (searchDropdown) {
            searchDropdown.style.display = "none";
            if (searchInput) searchInput.setAttribute("aria-expanded", "false");
        }

        document.querySelectorAll(".export-dropdown-wrapper").forEach((w) => {
            w.classList.remove("is-open");
            const b = w.querySelector(".export-dropdown-btn");
            if (b) b.setAttribute("aria-expanded", "false");
        });

        document.querySelectorAll(selectors.dropdownButton).forEach((button) => {
            button.setAttribute("aria-expanded", "false");
        });
    });
});