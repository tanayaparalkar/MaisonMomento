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
       ESCAPE KEY — CLOSE OPEN INTERFACES
       ========================================================================= */

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        closeDrawer();
        closeModal();

        document.querySelectorAll(selectors.dropdownButton).forEach((button) => {
            button.setAttribute("aria-expanded", "false");
        });
    });
});