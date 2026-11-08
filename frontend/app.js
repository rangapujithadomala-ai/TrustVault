
/* =========================================================
   TRUSTVAULT — SHARED APPLICATION JAVASCRIPT
   Themes, responsive sidebar and notification dropdown
   ========================================================= */

(function () {
    "use strict";

    const THEME_KEY = "trustvault-theme";
    const NOTIFICATIONS_URL = "/notifications/";

    const root = document.documentElement;

    /* -----------------------------------------------------
       1. THEME MANAGEMENT
       ----------------------------------------------------- */

    function readSavedTheme() {
        try {
            const saved = localStorage.getItem(THEME_KEY);
            return ["light", "dark", "system"].includes(saved)
                ? saved
                : "system";
        } catch (error) {
            return "system";
        }
    }

    function applyTheme(theme, save = true) {
        if (!["light", "dark", "system"].includes(theme)) {
            theme = "system";
        }

        root.setAttribute("data-theme", theme);

        if (save) {
            try {
                localStorage.setItem(THEME_KEY, theme);
            } catch (error) {
                console.warn("TrustVault could not save the theme preference.");
            }
        }

        document.querySelectorAll("[data-theme-choice]").forEach((button) => {
            const selected = button.dataset.themeChoice === theme;
            button.classList.toggle("active", selected);
            button.setAttribute("aria-pressed", String(selected));
        });

        document.querySelectorAll("[data-theme-select]").forEach((select) => {
            select.value = theme;
        });

        document.dispatchEvent(
            new CustomEvent("trustvault:themechange", {
                detail: { theme }
            })
        );
    }

    function initializeTheme() {
        applyTheme(readSavedTheme(), false);

        document.addEventListener("click", (event) => {
            const button = event.target.closest("[data-theme-choice]");

            if (!button) return;

            applyTheme(button.dataset.themeChoice);
        });

        document.querySelectorAll("[data-theme-select]").forEach((select) => {
            select.addEventListener("change", () => {
                applyTheme(select.value);
            });
        });
    }

    /* -----------------------------------------------------
       2. MOBILE SIDEBAR
       ----------------------------------------------------- */

    function initializeSidebar() {
        const sidebar = document.querySelector(".sidebar");
        const toggle = document.querySelector("[data-sidebar-toggle]");
        const overlay = document.querySelector("[data-sidebar-overlay]");

        if (!sidebar || !toggle) return;

        function closeSidebar() {
            sidebar.classList.remove("open");
            toggle.setAttribute("aria-expanded", "false");

            if (overlay) {
                overlay.classList.remove("visible");
                overlay.hidden = true;
            }
        }

        function openSidebar() {
            sidebar.classList.add("open");
            toggle.setAttribute("aria-expanded", "true");

            if (overlay) {
                overlay.hidden = false;
                overlay.classList.add("visible");
            }
        }

        toggle.addEventListener("click", () => {
            if (sidebar.classList.contains("open")) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });

        if (overlay) {
            overlay.addEventListener("click", closeSidebar);
        }

        sidebar.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                if (window.matchMedia("(max-width: 760px)").matches) {
                    closeSidebar();
                }
            });
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeSidebar();
        });

        window.addEventListener("resize", () => {
            if (!window.matchMedia("(max-width: 760px)").matches) {
                closeSidebar();
            }
        });
    }

    /* -----------------------------------------------------
       3. TOAST FEEDBACK
       ----------------------------------------------------- */

    function showToast(message, type = "success") {
        let container = document.querySelector("[data-toast-container]");

        if (!container) {
            container = document.createElement("div");
            container.dataset.toastContainer = "";
            container.setAttribute("aria-live", "polite");
            container.setAttribute("aria-atomic", "true");

            Object.assign(container.style, {
                position: "fixed",
                right: "20px",
                bottom: "20px",
                zIndex: "9999",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                maxWidth: "min(360px, calc(100vw - 40px))"
            });

            document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        toast.className = `alert alert-${type === "error" ? "error" : "success"}`;
        toast.textContent = message;

        Object.assign(toast.style, {
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "10px",
            padding: "12px 16px",
            boxShadow: "var(--shadow-md)",
            color: "var(--text)",
            overflowWrap: "anywhere"
        });

        container.appendChild(toast);

        window.setTimeout(() => {
            toast.remove();

            if (container && container.childElementCount === 0) {
                container.remove();
            }
        }, 3500);
    }

    /* -----------------------------------------------------
       4. CSRF TOKEN
       ----------------------------------------------------- */

    function getCsrfToken() {
        const metaToken = document.querySelector(
            'meta[name="csrf-token"]'
        );

        if (metaToken && metaToken.content) {
            return metaToken.content;
        }

        const inputToken = document.querySelector(
            'input[name="csrf_token"]'
        );

        if (inputToken && inputToken.value) {
            return inputToken.value;
        }

        return null;
    }

    /* -----------------------------------------------------
       5. NOTIFICATION ELEMENTS
       ----------------------------------------------------- */

    const notificationState = {
        items: [],
        unreadCount: 0,
        loading: false
    };

    function getNotificationElements() {
        return {
            toggle: document.querySelector("[data-notification-toggle]"),
            panel: document.querySelector("[data-notification-panel]"),
            list: document.querySelector("[data-notification-list]"),
            count: document.querySelector("[data-notification-count]"),
            markAll: document.querySelector("[data-notification-mark-all]"),
            clearRead: document.querySelector("[data-notification-clear-read]"),
            clearAll: document.querySelector("[data-notification-clear-all]")
        };
    }

    function updateUnreadCount(count) {
        const elements = getNotificationElements();

        notificationState.unreadCount = Math.max(0, Number(count) || 0);

        if (!elements.count) return;

        elements.count.textContent =
            notificationState.unreadCount > 99
                ? "99+"
                : String(notificationState.unreadCount);

        elements.count.hidden = notificationState.unreadCount === 0;

        if (elements.toggle) {
            elements.toggle.setAttribute(
                "aria-label",
                notificationState.unreadCount > 0
                    ? `Notifications, ${notificationState.unreadCount} unread`
                    : "Notifications"
            );
        }
    }

    function formatNotificationDate(value) {
        if (!value) return "Date unavailable";

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return "Date unavailable";
        }

        return date.toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short"
        });
    }

    function renderNotificationList() {
        const elements = getNotificationElements();

        if (!elements.list) return;

        elements.list.replaceChildren();

        if (notificationState.loading) {
            const loading = document.createElement("div");
            loading.className = "loading-state";
            loading.textContent = "Loading notifications...";
            elements.list.appendChild(loading);
            return;
        }

        if (notificationState.items.length === 0) {
            const empty = document.createElement("div");
            empty.className = "empty-state";

            const message = document.createElement("p");
            message.textContent = "You're all caught up.";

            empty.appendChild(message);
            elements.list.appendChild(empty);
            return;
        }

        notificationState.items.forEach((item) => {
            const row = document.createElement("div");
            row.className = "notification-item";
            row.classList.toggle("unread", !item.read);

            const marker = document.createElement("span");
            marker.className = "activity-marker";
            marker.textContent = item.read ? "✓" : "●";
            marker.setAttribute("aria-hidden", "true");

            const content = document.createElement("div");
            content.style.flex = "1";
            content.style.minWidth = "0";

            const message = document.createElement("p");
            message.className = "notification-message";
            message.textContent = item.message || "Notification";

            const time = document.createElement("p");
            time.className = "notification-time";
            time.textContent = formatNotificationDate(item.created_at);

            content.append(message, time);

            const actions = document.createElement("div");
            actions.className = "flex-wrap";

            if (!item.read) {
                const readButton = document.createElement("button");
                readButton.type = "button";
                readButton.className = "btn btn-ghost btn-sm";
                readButton.textContent = "Mark read";
                readButton.dataset.notificationRead = item.id;
                readButton.setAttribute(
                    "aria-label",
                    "Mark notification as read"
                );
                actions.appendChild(readButton);
            }

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "btn btn-ghost btn-sm";
            deleteButton.textContent = "Delete";
            deleteButton.dataset.notificationDelete = item.id;
            deleteButton.setAttribute(
                "aria-label",
                "Delete notification"
            );
            actions.appendChild(deleteButton);

            row.append(marker, content, actions);
            elements.list.appendChild(row);
        });
    }

    /* -----------------------------------------------------
       6. NOTIFICATION API REQUESTS
       ----------------------------------------------------- */

    async function notificationRequest(url, options = {}) {
        const headers = new Headers(options.headers || {});

        headers.set("Accept", "application/json");

        if (options.method && options.method !== "GET") {
            const token = getCsrfToken();

            if (!token) {
                throw new Error(
                    "Security token is missing. Refresh the page and try again."
                );
            }

            headers.set("X-CSRFToken", token);
        }

        const response = await fetch(url, {
            ...options,
            headers,
            credentials: "same-origin"
        });

        let data = {};

        try {
            data = await response.json();
        } catch (error) {
            data = {};
        }

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error("Your session has expired. Please log in again.");
            }

            if (response.status === 403) {
                throw new Error("The request was not permitted.");
            }

            throw new Error(
                data.error || data.message || `Request failed (${response.status}).`
            );
        }

        return data;
    }

    async function loadNotifications(showLoading = false) {
        const elements = getNotificationElements();

        if (!elements.list) return;

        if (notificationState.loading) return;

        notificationState.loading = showLoading;

        if (showLoading) renderNotificationList();

        try {
            const data = await notificationRequest(NOTIFICATIONS_URL);

            notificationState.items = Array.isArray(data.notifications)
                ? data.notifications
                : [];

            updateUnreadCount(data.unread_count);
        } catch (error) {
            if (showLoading) {
                elements.list.replaceChildren();

                const message = document.createElement("div");
                message.className = "alert alert-error";
                message.textContent = error.message;

                elements.list.appendChild(message);
            }

            console.error("TrustVault notification loading failed:", error);
        } finally {
            notificationState.loading = false;
            renderNotificationList();
        }
    }

    async function performNotificationAction(url, method, successMessage) {
        try {
            await notificationRequest(url, { method });

            showToast(successMessage);
            await loadNotifications();
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    async function markNotificationRead(id) {
        await performNotificationAction(
            `${NOTIFICATIONS_URL}${encodeURIComponent(id)}/read`,
            "POST",
            "Notification marked as read."
        );
    }

    async function deleteNotification(id) {
        await performNotificationAction(
            `${NOTIFICATIONS_URL}${encodeURIComponent(id)}`,
            "DELETE",
            "Notification deleted."
        );
    }

    async function markAllNotificationsRead() {
        await performNotificationAction(
            `${NOTIFICATIONS_URL}read-all`,
            "POST",
            "All notifications marked as read."
        );
    }

    async function clearReadNotifications() {
        await performNotificationAction(
            `${NOTIFICATIONS_URL}clear-read`,
            "POST",
            "Read notifications cleared."
        );
    }

    async function clearAllNotifications() {
        const confirmed = window.confirm(
            "Are you sure you want to delete all notifications?"
        );

        if (!confirmed) return;

        await performNotificationAction(
            `${NOTIFICATIONS_URL}clear-all`,
            "POST",
            "All notifications cleared."
        );
    }

    /* -----------------------------------------------------
       7. NOTIFICATION DROPDOWN EVENTS
       ----------------------------------------------------- */

    function initializeNotifications() {
        const elements = getNotificationElements();

        if (!elements.toggle || !elements.panel) return;

        function closePanel() {
            elements.panel.hidden = true;
            elements.toggle.setAttribute("aria-expanded", "false");
        }

        function openPanel() {
            elements.panel.hidden = false;
            elements.toggle.setAttribute("aria-expanded", "true");
            loadNotifications(true);
        }

        elements.toggle.addEventListener("click", () => {
            if (elements.panel.hidden) {
                openPanel();
            } else {
                closePanel();
            }
        });

        document.addEventListener("click", (event) => {
            const wrapper = elements.toggle.closest(".notification-wrapper");

            if (
                !elements.panel.hidden &&
                wrapper &&
                !wrapper.contains(event.target)
            ) {
                closePanel();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closePanel();
        });

        if (elements.markAll) {
            elements.markAll.addEventListener(
                "click",
                markAllNotificationsRead
            );
        }

        if (elements.clearRead) {
            elements.clearRead.addEventListener(
                "click",
                clearReadNotifications
            );
        }

        if (elements.clearAll) {
            elements.clearAll.addEventListener(
                "click",
                clearAllNotifications
            );
        }

        if (elements.list) {
            elements.list.addEventListener("click", (event) => {
                const readButton = event.target.closest(
                    "[data-notification-read]"
                );

                if (readButton) {
                    markNotificationRead(readButton.dataset.notificationRead);
                    return;
                }

                const deleteButton = event.target.closest(
                    "[data-notification-delete]"
                );

                if (deleteButton) {
                    deleteNotification(
                        deleteButton.dataset.notificationDelete
                    );
                }
            });
        }

        loadNotifications();
    }

    /* -----------------------------------------------------
       8. INITIALIZE APPLICATION
       ----------------------------------------------------- */

    function initializeTrustVault() {
        initializeTheme();
        initializeSidebar();
        initializeNotifications();

        document.dispatchEvent(
            new CustomEvent("trustvault:ready")
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initializeTrustVault,
            { once: true }
        );
    } else {
        initializeTrustVault();
    }

    /* Public methods for page-specific scripts. */
    window.TrustVault = Object.freeze({
        applyTheme,
        loadNotifications,
        showToast
    });

})();
