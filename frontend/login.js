
// ==================================
// GET HTML ELEMENTS
// ==================================

const loginForm = document.getElementById("loginForm");

const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");

const togglePassword = document.getElementById("togglePassword");

const message = document.getElementById("message");

// ==================================
// PASSWORD SHOW / HIDE
// ==================================

togglePassword.addEventListener("click", function () {

    const isPasswordHidden = passwordInput.type === "password";

    if (isPasswordHidden) {
        passwordInput.type = "text";
        togglePassword.setAttribute("aria-label", "Hide password");
        togglePassword.setAttribute("aria-pressed", "true");
    } else {
        passwordInput.type = "password";
        togglePassword.setAttribute("aria-label", "Show password");
        togglePassword.setAttribute("aria-pressed", "false");
    }

});

// ==================================
// MESSAGE FUNCTION
// ==================================

function showMessage(text, type) {

    message.textContent = text;
    message.className = "message " + type;

}

// ==================================
// LOGIN FORM VALIDATION
// ==================================

loginForm.addEventListener("submit", function (event) {

    event.preventDefault();

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    // Check empty fields
    if (!email || !password) {

        showMessage(
            "Please enter your email and password.",
            "error"
        );

        return;
    }

    // Validate email format
const emailPattern = /^[A-Za-z0-9._%+-]+@[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z][A-Za-z0-9-]*)*\.[A-Za-z]{2,}$/;

    if (!emailPattern.test(email)) {

        showMessage(
            "Please enter a valid email address.",
            "error"
        );

        return;
    }

    // No password length or strength check during login

    // Actual login will happen after Flask integration
    showMessage(
        "Input validation successful. Backend connection is required to sign in.",
        "success"
    );

});
