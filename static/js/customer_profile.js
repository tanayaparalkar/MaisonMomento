/**
 * static/js/customer_profile.js
 * ==============================
 * Interactive behaviors for the client profile drawer and /account/ page:
 * - Slide-out drawer open/close with keyboard (ESC) and backdrop click handling
 * - In-drawer Sign In / Register tabs
 * - Seamless AJAX authentication with inline error display and automatic redirect
 * - Forgot password modal toggle
 * - Instant profile photo upload & live preview
 */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", () => {
        const drawer = document.getElementById("customer-profile-drawer");
        const backdrop = document.getElementById("cp-drawer-backdrop");
        const panel = document.getElementById("cp-drawer-panel");
        const closeBtn = document.getElementById("cp-drawer-close-btn");
        const triggerBtn = document.getElementById("customer-profile-trigger");

        // --- DRAWER OPEN / CLOSE CONTROLS ---
        const openDrawer = () => {
            if (!drawer) return;
            drawer.classList.add("is-open");
            drawer.setAttribute("aria-hidden", "false");
            document.body.style.overflow = "hidden";

            // Focus on first input if in guest mode
            setTimeout(() => {
                const firstInput = drawer.querySelector(".cp-tab-pane.active input:not([type='hidden'])");
                if (firstInput) firstInput.focus();
            }, 100);
        };

        const closeDrawer = () => {
            if (!drawer) return;
            drawer.classList.remove("is-open");
            drawer.setAttribute("aria-hidden", "true");
            document.body.style.overflow = "";
            if (triggerBtn) triggerBtn.focus();
        };

        if (triggerBtn) {
            triggerBtn.addEventListener("click", (e) => {
                e.preventDefault();
                openDrawer();
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener("click", (e) => {
                e.preventDefault();
                closeDrawer();
            });
        }

        if (backdrop) {
            backdrop.addEventListener("click", (e) => {
                e.preventDefault();
                closeDrawer();
            });
        }

        // Global ESC key listener for profile drawer
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                if (drawer && drawer.classList.contains("is-open")) {
                    closeDrawer();
                }
                const forgotModal = document.getElementById("cp-forgot-modal");
                if (forgotModal && forgotModal.style.display !== "none") {
                    forgotModal.style.display = "none";
                }
            }
        });

        // --- GUEST DRAWER: TABS SWITCHING ---
        const tabSignIn = document.getElementById("cp-tab-signin");
        const tabRegister = document.getElementById("cp-tab-register");
        const paneSignIn = document.getElementById("cp-pane-signin");
        const paneRegister = document.getElementById("cp-pane-register");
        const authErrorBox = document.getElementById("cp-auth-error");

        const switchTab = (toTab) => {
            if (authErrorBox) {
                authErrorBox.style.display = "none";
                authErrorBox.textContent = "";
            }

            if (toTab === "signin") {
                if (tabSignIn) {
                    tabSignIn.classList.add("active");
                    tabSignIn.setAttribute("aria-selected", "true");
                }
                if (tabRegister) {
                    tabRegister.classList.remove("active");
                    tabRegister.setAttribute("aria-selected", "false");
                }
                if (paneSignIn) paneSignIn.style.display = "block";
                if (paneRegister) paneRegister.style.display = "none";
                const input = paneSignIn ? paneSignIn.querySelector("input:not([type='hidden'])") : null;
                if (input) input.focus();
            } else {
                if (tabRegister) {
                    tabRegister.classList.add("active");
                    tabRegister.setAttribute("aria-selected", "true");
                }
                if (tabSignIn) {
                    tabSignIn.classList.remove("active");
                    tabSignIn.setAttribute("aria-selected", "false");
                }
                if (paneSignIn) paneSignIn.style.display = "none";
                if (paneRegister) paneRegister.style.display = "block";
                const input = paneRegister ? paneRegister.querySelector("input:not([type='hidden'])") : null;
                if (input) input.focus();
            }
        };

        if (tabSignIn) {
            tabSignIn.addEventListener("click", () => switchTab("signin"));
        }
        if (tabRegister) {
            tabRegister.addEventListener("click", () => switchTab("register"));
        }

        // --- FORGOT PASSWORD MODAL ---
        const forgotBtn = document.getElementById("cp-forgot-btn");
        const forgotModal = document.getElementById("cp-forgot-modal");
        const forgotCloseBtn = document.getElementById("cp-forgot-close-btn");
        const forgotBackdrop = document.getElementById("cp-forgot-backdrop");

        if (forgotBtn && forgotModal) {
            forgotBtn.addEventListener("click", (e) => {
                e.preventDefault();
                forgotModal.style.display = "flex";
            });
        }
        if (forgotCloseBtn && forgotModal) {
            forgotCloseBtn.addEventListener("click", () => {
                forgotModal.style.display = "none";
            });
        }
        if (forgotBackdrop && forgotModal) {
            forgotBackdrop.addEventListener("click", () => {
                forgotModal.style.display = "none";
            });
        }

        // --- IN-DRAWER AJAX AUTHENTICATION ---
        const showAuthError = (message) => {
            if (!authErrorBox) return;
            authErrorBox.textContent = message || "An unexpected error occurred. Please try again.";
            authErrorBox.style.display = "block";
        };

        const handleAuthSubmit = (form, submitBtn, defaultBtnText) => {
            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                if (authErrorBox) authErrorBox.style.display = "none";

                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = `<span>Processing...</span>`;
                }

                try {
                    const formData = new FormData(form);
                    const response = await fetch(form.action, {
                        method: "POST",
                        body: formData,
                        headers: {
                            "X-Requested-With": "XMLHttpRequest",
                        },
                    });

                    const data = await response.json();

                    if (response.ok && data.success) {
                        // Smoothly redirect or reload
                        window.location.href = data.redirect_url || window.location.href;
                    } else {
                        showAuthError(data.error || "Authentication failed. Please verify your details.");
                        if (submitBtn) {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = defaultBtnText;
                        }
                    }
                } catch (err) {
                    console.error("Auth error:", err);
                    showAuthError("Connection error. Please try again or refresh the page.");
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = defaultBtnText;
                    }
                }
            });
        };

        const signinForm = document.getElementById("cp-signin-form");
        const signinSubmit = document.getElementById("cp-signin-submit");
        if (signinForm && signinSubmit) {
            handleAuthSubmit(signinForm, signinSubmit, `<span>Sign In</span> <span class="cp-btn-arrow">&rarr;</span>`);
        }

        const registerForm = document.getElementById("cp-register-form");
        const registerSubmit = document.getElementById("cp-register-submit");
        if (registerForm && registerSubmit) {
            handleAuthSubmit(registerForm, registerSubmit, `<span>Create Account</span> <span class="cp-btn-arrow">&rarr;</span>`);
        }

        // --- PROFILE PHOTO UPLOAD HANDLING (/account/) ---
        const avatarInput = document.getElementById("cp-avatar-input");
        const avatarForm = document.getElementById("cp-avatar-form");
        if (avatarInput && avatarForm) {
            avatarInput.addEventListener("change", () => {
                if (avatarInput.files && avatarInput.files[0]) {
                    const file = avatarInput.files[0];

                    // Instant client preview
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const previewImg = document.getElementById("cp-avatar-preview");
                        const placeholder = document.getElementById("cp-avatar-placeholder");
                        if (previewImg) {
                            previewImg.src = e.target.result;
                        } else if (placeholder) {
                            const newImg = document.createElement("img");
                            newImg.src = e.target.result;
                            newImg.className = "cp-avatar-img-large";
                            newImg.id = "cp-avatar-preview";
                            placeholder.parentNode.replaceChild(newImg, placeholder);
                        }
                    };
                    reader.readAsDataURL(file);

                    // Submit form
                    avatarForm.submit();
                }
            });
        }
    });
})();
