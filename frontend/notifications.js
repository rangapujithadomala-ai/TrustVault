document.addEventListener("DOMContentLoaded", () => {

    const bell = document.getElementById("notificationBell");
    const dropdown = document.getElementById("notificationDropdown");
    const count = document.getElementById("notificationCount");
    const list = document.getElementById("notificationList");
    const markAllButton = document.getElementById("markAllRead");

    if (!bell || !dropdown || !count || !list) {
        return;
    }

    const csrfToken = document.querySelector(
        'meta[name="csrf-token"]'
    )?.content || "";

    let notifications = [];
    let currentFilter = "all";

    async function loadNotifications() {

        try {

            const response = await fetch("/notifications/", {
                method: "GET",
                credentials: "same-origin"
            });

            if (!response.ok) {
                throw new Error("Unable to load notifications.");
            }

            const data = await response.json();

            notifications = data.notifications || [];

            updateCount(data.unread_count || 0);
            renderNotifications();

        } catch (error) {

            list.textContent = "Unable to load notifications.";

        }
    }

    function updateCount(unreadCount) {

        count.textContent = unreadCount;
        count.hidden = unreadCount === 0;

    }

    function renderNotifications() {

        list.replaceChildren();

        const filtered = notifications.filter(item => {

            if (currentFilter === "unread") {
                return !item.read;
            }

            if (currentFilter === "read") {
                return item.read;
            }

            return true;

        });

        if (filtered.length === 0) {

            const empty = document.createElement("p");

            empty.className = "notification-empty";
            empty.textContent = "No notifications found.";

            list.appendChild(empty);

            return;
        }

        filtered.forEach(item => {

            const notification = document.createElement("button");

            notification.type = "button";

            notification.className =
                "notification-item" +
                (item.read ? " is-read" : " is-unread");

            const message = document.createElement("span");

            message.className = "notification-message";
            message.textContent = item.message;

            const date = document.createElement("small");

            date.className = "notification-date";

            date.textContent = item.created_at
                ? new Date(item.created_at).toLocaleString()
                : "";

            notification.appendChild(message);
            notification.appendChild(date);

            notification.addEventListener("click", async () => {

                if (!item.read) {

                    await fetch(
                        `/notifications/${encodeURIComponent(item.id)}/read`,
                        {
                            method: "POST",
                            credentials: "same-origin",
                            headers: {
                                "X-CSRFToken": csrfToken
                            }
                        }
                    );

                    await loadNotifications();

                }

            });

            list.appendChild(notification);

        });

    }

    bell.addEventListener("click", () => {

        dropdown.hidden = !dropdown.hidden;

        if (!dropdown.hidden) {
            loadNotifications();
        }

    });

    document.querySelectorAll(".notification-filter")
        .forEach(button => {

            button.addEventListener("click", () => {

                currentFilter = button.dataset.filter;

                document.querySelectorAll(".notification-filter")
                    .forEach(item => {
                        item.classList.remove("active");
                    });

                button.classList.add("active");

                renderNotifications();

            });

        });

    if (markAllButton) {

        markAllButton.addEventListener("click", async () => {

            try {

                const response = await fetch("/notifications/read-all", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "X-CSRFToken": csrfToken
                    }
                });

                if (!response.ok) {
                    throw new Error("Unable to update notifications.");
                }

                await loadNotifications();

            } catch (error) {

                alert("Unable to mark notifications as read.");

            }

        });

    }

    document.addEventListener("click", event => {

        if (
            !event.target.closest(".notification-wrapper")
        ) {
            dropdown.hidden = true;
        }

    });

    loadNotifications();

});