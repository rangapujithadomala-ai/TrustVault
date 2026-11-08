
document.addEventListener("DOMContentLoaded", () => {
    const bell = document.getElementById("notificationBell");
    const dropdown = document.getElementById("notificationDropdown");
    const count = document.getElementById("notificationCount");
    const list = document.getElementById("notificationList");
    const markAllButton = document.getElementById("markAllRead");

    if (!bell || !dropdown || !count || !list) {
        return;
    }

    const csrfToken =
        document.querySelector('meta[name="csrf-token"]')?.content || "";

    let notifications = [];
    let currentFilter = "all";
    let isLoading = false;

    async function request(url, method = "POST") {
        const options = {
            method,
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": csrfToken
            }
        };

        return fetch(url, options);
    }

    function updateUnreadCount(serverCount = null) {
        const unreadCount =
            Number.isFinite(Number(serverCount))
                ? Math.max(0, Number(serverCount))
                : notifications.filter(item => !item.read).length;

        count.textContent = String(unreadCount);
        count.hidden = unreadCount === 0;

        bell.setAttribute(
            "aria-label",
            unreadCount > 0
                ? `Notifications, ${unreadCount} unread`
                : "Notifications"
        );
    }

    async function loadNotifications() {
        if (isLoading) {
            return;
        }

        isLoading = true;

        try {
            const response = await fetch("/notifications/", {
                credentials: "same-origin",
                headers: {
                    "Accept": "application/json"
                }
            });

            if (!response.ok) {
                throw new Error("Unable to load notifications.");
            }

            const data = await response.json();

            notifications = Array.isArray(data.notifications)
                ? data.notifications
                : [];

            updateUnreadCount(data.unread_count);
            renderNotifications();
        } catch (error) {
            console.error("Notification loading error:", error);
            list.textContent = "Unable to load notifications.";
        } finally {
            isLoading = false;
        }
    }

    function renderNotifications() {
        list.replaceChildren();

        const filteredNotifications = notifications.filter(item => {
            if (currentFilter === "unread") {
                return !item.read;
            }

            if (currentFilter === "read") {
                return Boolean(item.read);
            }

            return true;
        });

        if (filteredNotifications.length === 0) {
            const emptyMessage = document.createElement("p");
            emptyMessage.className = "notification-empty";
            emptyMessage.textContent = "No notifications found.";
            list.appendChild(emptyMessage);
            return;
        }

        filteredNotifications.forEach(item => {
            const row = document.createElement("div");
            row.className = "notification-row";

            const notificationButton = document.createElement("button");
            notificationButton.type = "button";
            notificationButton.className =
                "notification-item " +
                (item.read ? "is-read" : "is-unread");

            const message = document.createElement("span");
            message.className = "notification-message";
            message.textContent = item.message || "Notification";

            const date = document.createElement("small");
            date.className = "notification-date";

            if (item.created_at) {
                const parsedDate = new Date(item.created_at);

                date.textContent = Number.isNaN(parsedDate.getTime())
                    ? ""
                    : parsedDate.toLocaleString();
            } else {
                date.textContent = "";
            }

            notificationButton.append(message, date);

            notificationButton.addEventListener("click", async () => {
                if (item.read || notificationButton.disabled) {
                    return;
                }

                notificationButton.disabled = true;

                try {
                    const response = await request(
                        `/notifications/${encodeURIComponent(item.id)}/read`
                    );

                    if (!response.ok) {
                        throw new Error("Unable to mark notification as read.");
                    }

                    await loadNotifications();
                } catch (error) {
                    console.error(error);
                    notificationButton.disabled = false;
                }
            });

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "notification-delete";
            deleteButton.textContent = "Delete";
            deleteButton.setAttribute(
                "aria-label",
                "Delete notification"
            );

            deleteButton.addEventListener("click", async () => {
                if (deleteButton.disabled) {
                    return;
                }

                deleteButton.disabled = true;

                try {
                    const response = await request(
                        `/notifications/${encodeURIComponent(item.id)}`,
                        "DELETE"
                    );

                    if (!response.ok) {
                        throw new Error("Unable to delete notification.");
                    }

                    await loadNotifications();
                } catch (error) {
                    console.error(error);
                    deleteButton.disabled = false;
                }
            });

            row.append(notificationButton, deleteButton);
            list.appendChild(row);
        });
    }

    function closeDropdown() {
        dropdown.hidden = true;
        dropdown.classList.remove("show");
        bell.setAttribute("aria-expanded", "false");
    }

    bell.setAttribute("aria-expanded", "false");

    bell.addEventListener("click", () => {
        const shouldOpen = dropdown.hidden;

        dropdown.hidden = !shouldOpen;
        dropdown.classList.toggle("show", shouldOpen);
        bell.setAttribute("aria-expanded", String(shouldOpen));

        if (shouldOpen) {
            loadNotifications();
        }
    });

    document.querySelectorAll(".notification-filter").forEach(button => {
        button.addEventListener("click", () => {
            const selectedFilter = button.dataset.filter;

            if (!["all", "unread", "read"].includes(selectedFilter)) {
                return;
            }

            currentFilter = selectedFilter;

            document.querySelectorAll(".notification-filter").forEach(
                filterButton => {
                    const isActive = filterButton === button;

                    filterButton.classList.toggle("active", isActive);
                    filterButton.setAttribute(
                        "aria-pressed",
                        String(isActive)
                    );
                }
            );

            renderNotifications();
        });
    });

    markAllButton?.addEventListener("click", async () => {
        if (markAllButton.disabled) {
            return;
        }

        markAllButton.disabled = true;

        try {
            const response = await request("/notifications/read-all");

            if (!response.ok) {
                throw new Error("Unable to mark all notifications as read.");
            }

            await loadNotifications();
        } catch (error) {
            console.error(error);
        } finally {
            markAllButton.disabled = false;
        }
    });

    document
        .getElementById("clearReadNotifications")
        ?.addEventListener("click", async event => {
            const button = event.currentTarget;

            if (button.disabled) {
                return;
            }

            button.disabled = true;

            try {
                const response = await request(
                    "/notifications/clear-read"
                );

                if (!response.ok) {
                    throw new Error("Unable to clear read notifications.");
                }

                await loadNotifications();
            } catch (error) {
                console.error(error);
            } finally {
                button.disabled = false;
            }
        });

    document
        .getElementById("clearAllNotifications")
        ?.addEventListener("click", async event => {
            const button = event.currentTarget;

            if (button.disabled) {
                return;
            }

            const confirmed = window.confirm(
                "Clear all your notifications? This does not delete documents or audit records."
            );

            if (!confirmed) {
                return;
            }

            button.disabled = true;

            try {
                const response = await request(
                    "/notifications/clear-all"
                );

                if (!response.ok) {
                    throw new Error("Unable to clear notifications.");
                }

                await loadNotifications();
            } catch (error) {
                console.error(error);
            } finally {
                button.disabled = false;
            }
        });

    document.addEventListener("click", event => {
        const target = event.target;

        if (
            target instanceof Element &&
            !target.closest(".notification-wrapper")
        ) {
            closeDropdown();
        }
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && !dropdown.hidden) {
            closeDropdown();
            bell.focus();
        }
    });

    loadNotifications();
});
