
document.addEventListener("DOMContentLoaded", function () {
    const themeSelect = document.getElementById("themeSelect");
    const themeKey = "trustvault-theme";
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");

    function applyTheme(theme) {
        const useDarkMode =
            theme === "dark" ||
            (theme === "system" && systemTheme.matches);

        document.body.classList.toggle("dark-mode", useDarkMode);
    }

    function loadTheme() {
        const savedTheme = localStorage.getItem(themeKey) || "light";

        applyTheme(savedTheme);

        if (themeSelect) {
            themeSelect.value = savedTheme;
        }
    }

    loadTheme();

    if (themeSelect) {
        themeSelect.addEventListener("change", function () {
            const selectedTheme = themeSelect.value;

            localStorage.setItem(themeKey, selectedTheme);
            applyTheme(selectedTheme);
        });
    }

    systemTheme.addEventListener("change", function () {
        const savedTheme = localStorage.getItem(themeKey) || "light";

        if (savedTheme === "system") {
            applyTheme("system");
        }
    });

    window.addEventListener("storage", function (event) {
        if (event.key === themeKey) {
            loadTheme();
        }
    });
});
