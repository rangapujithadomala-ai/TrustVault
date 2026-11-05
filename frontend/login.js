
const loginForm = document.getElementById("loginForm");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const togglePassword = document.getElementById("togglePassword");
const message = document.getElementById("message");
const submitButton = document.getElementById("submitButton");

function showMessage(text, type) {
    message.textContent = text;
    message.className = "message " + type;
}

// Show or hide password
if (togglePassword) {
    togglePassword.addEventListener("click", function () {
        const isPassword = passwordInput.type === "password";

        passwordInput.type = isPassword ? "text" : "password";
        togglePassword.setAttribute(
            "aria-label",
            isPassword ? "Hide password" : "Show password"
        );
    });
}

// Login form submission
loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    message.className = "message";

    if (!email || !password) {
        showMessage("Please enter your email and password.", "error");
        return;
    }

    if (!emailPattern.test(email)) {
        showMessage("Please enter a valid email address.", "error");
        return;
    }

    const csrfToken = document.querySelector(
        'meta[name="csrf-token"]'
    )?.content;

    if (!csrfToken) {
        showMessage("Security token missing. Please refresh the page.", "error");
        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Signing in...";

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            showMessage(
                data.message || "Login failed. Please check your details.",
                "error"
            );
            return;
        }

        showMessage("Login successful. Redirecting...", "success");

        if (data.redirect) {
            window.location.href = data.redirect;
        } else {
            showMessage("Login response did not contain a redirect.", "error");
        }

    } catch (error) {
        showMessage(
            "Unable to connect to the server. Please try again.",
            "error"
        );
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Sign In";
    }
});
