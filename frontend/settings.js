
document.addEventListener("DOMContentLoaded", function () {

    const themeSelect = document.getElementById("themeSelect");

    // Apply the saved theme
    const savedTheme = localStorage.getItem("trustvault-theme") || "light";

    document.body.classList.toggle("dark-mode", savedTheme === "dark");

    if (themeSelect) {
        themeSelect.value = savedTheme;

        themeSelect.addEventListener("change", function () {
            const selectedTheme = themeSelect.value;

            localStorage.setItem("trustvault-theme", selectedTheme);

            document.body.classList.toggle(
                "dark-mode",
                selectedTheme === "dark"
            );
        });
    }

});
