/* =========================================================
   TRUSTVAULT — SETTINGS AND SHARED PAGE BEHAVIOUR
   Theme controls + CSRF-protected logout
   ========================================================= */

(function () {
    "use strict";

    const THEME_KEY = "trustvault-theme";
    const VALID_THEMES = ["light", "dark", "system"];

    function getSavedTheme() {
        const savedTheme = localStorage.getItem(THEME_KEY);

        return VALID_THEMES.includes(savedTheme)
            ? savedTheme
            : "system";
    }

    function getResolvedTheme(theme) {
        if (theme === "system") {
            return window.matchMedia &&
                window.matchMedia("(prefers-color-scheme: dark)").matches
                ? "dark"
                : "light";
        }

        return theme;
    }

    function applyTheme(theme) {
        if (!VALID_THEMES.includes(theme)) {
            theme = "system";
        }

        const resolvedTheme = getResolvedTheme(theme);

        document.documentElement.setAttribute("data-theme", theme);

        // Login page uses body.dark-mode in its existing styles.
        document.body.classList.toggle(
            "dark-mode",
            resolvedTheme === "dark"
        );

        document.querySelectorAll("[data-theme-choice]").forEach(function (button) {
            const isActive = button.dataset.themeChoice === theme;

            button.classList.toggle("active", isActive);
            button.setAttribute("aria-pressed", String(isActive));
        });

        const themeLabel = document.getElementById("themeLabel");
        const themeIcon = document.getElementById("themeIcon");

        if (themeLabel) {
            themeLabel.textContent =
                theme.charAt(0).toUpperCase() + theme.slice(1);
        }

        if (themeIcon) {
            themeIcon.textContent =
                resolvedTheme === "dark" ? "☾" : "☀";
        }
    }

    function saveTheme(theme) {
        if (!VALID_THEMES.includes(theme)) {
            return;
        }

        localStorage.setItem(THEME_KEY, theme);
        applyTheme(theme);
    }

    function addRegistrationThemeToggle() {
        if (!document.body.classList.contains("register-page")) {
            return;
        }

        if (document.getElementById("registerThemeToggle")) {
            return;
        }

        const button = document.createElement("button");

        button.id = "registerThemeToggle";
        button.type = "button";
        button.setAttribute("aria-label", "Toggle appearance");
        button.title = "Switch between light and dark mode";

        Object.assign(button.style, {
            position: "fixed",
            top: "18px",
            right: "20px",
            zIndex: "9999",
            width: "42px",
            height: "42px",
            borderRadius: "50%",
            border: "1px solid var(--border)",
            background: "var(--surface)",
            color: "var(--text)",
            boxShadow: "0 3px 12px rgba(0,0,0,.12)",
            cursor: "pointer",
            fontSize: "19px"
        });

        button.addEventListener("click", function () {
            const currentTheme = getSavedTheme();
            const resolvedTheme = getResolvedTheme(currentTheme);

            saveTheme(resolvedTheme === "dark" ? "light" : "dark");
        });

        document.body.appendChild(button);
        updateRegistrationThemeIcon();
    }

    function updateRegistrationThemeIcon() {
        const button = document.getElementById("registerThemeToggle");

        if (!button) {
            return;
        }

        const resolvedTheme = getResolvedTheme(getSavedTheme());

        button.textContent = resolvedTheme === "dark" ? "☀" : "☾";
        button.setAttribute(
            "aria-label",
            resolvedTheme === "dark"
                ? "Switch to light mode"
                : "Switch to dark mode"
        );
    }

    function setupThemeControls() {
        applyTheme(getSavedTheme());

        document.querySelectorAll("[data-theme-choice]").forEach(function (button) {
            button.addEventListener("click", function () {
                saveTheme(button.dataset.themeChoice);
                updateRegistrationThemeIcon();
            });
        });

        addRegistrationThemeToggle();

        if (window.matchMedia) {
            const systemPreference = window.matchMedia(
                "(prefers-color-scheme: dark)"
            );

            systemPreference.addEventListener("change", function () {
                if (getSavedTheme() === "system") {
                    applyTheme("system");
                    updateRegistrationThemeIcon();
                }
            });
        }
    }

    function setupLogout() {
        document.querySelectorAll('a[href="/auth/logout"]').forEach(function (link) {
            link.addEventListener("click", async function (event) {
                event.preventDefault();

                const csrf =
                    document.querySelector('meta[name="csrf-token"]')?.content || "";

                try {
                    const response = await fetch("/auth/logout", {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "X-CSRFToken": csrf
                        }
                    });

                    if (!response.ok) {
                        throw new Error("Logout request was rejected.");
                    }

                    window.location.href = "/login.html?logout=1";
                } catch (error) {
                    alert(
                        "Unable to log out. Please refresh the page and try again."
                    );
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setupThemeControls();
        setupLogout();
    });
})();