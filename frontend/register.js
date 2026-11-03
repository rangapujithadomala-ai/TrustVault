
// ==================================
// GET HTML ELEMENTS
// ==================================

const registerForm = document.getElementById("registerForm");

const fullName = document.getElementById("fullName");
const email = document.getElementById("email");
const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirmPassword");

const togglePassword = document.getElementById("togglePassword");
const toggleConfirmPassword = document.getElementById("toggleConfirmPassword");

const strengthIndicator = document.getElementById("strengthIndicator");
const strengthText = document.getElementById("strengthText");

const message = document.getElementById("message");
const submitButton = document.getElementById("submitButton");

// ==================================
// EYE ICONS
// ==================================

const eyeIcon = `
<svg class="eye-icon" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/>
    <circle cx="12" cy="12" r="3"/>
</svg>
`;

const eyeOffIcon = `
<svg class="eye-icon" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M3 3l18 18"/>
    <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/>
    <path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c6.5 0 10 7 10 7a15.5 15.5 0 0 1-3.1 3.8"/>
    <path d="M6.2 6.2C3.5 8 2 12 2 12s3.5 7 10 7c1.1 0 2.1-.2 3-.5"/>
</svg>
`;

// ==================================
// PASSWORD SHOW / HIDE FUNCTION
// ==================================

function setupPasswordToggle(button, input, fieldName) {
    button.addEventListener("click", function () {
        const isHidden = input.type === "password";

        if (isHidden) {
            input.type = "text";
            button.innerHTML = eyeOffIcon;
            button.setAttribute("aria-label", "Hide " + fieldName);
            button.setAttribute("aria-pressed", "true");
        } else {
            input.type = "password";
            button.innerHTML = eyeIcon;
            button.setAttribute("aria-label", "Show " + fieldName);
            button.setAttribute("aria-pressed", "false");
        }
    });
}

setupPasswordToggle(togglePassword, password, "password");

setupPasswordToggle(
    toggleConfirmPassword,
    confirmPassword,
    "confirm password"
);

// ==================================
// PASSWORD STRENGTH CHECKER
// ==================================

password.addEventListener("input", function () {
    const value = password.value;
    let score = 0;

    if (value.length >= 8) score++;
    if (/[A-Z]/.test(value)) score++;
    if (/[a-z]/.test(value)) score++;
    if (/[0-9]/.test(value)) score++;
    if (/[^A-Za-z0-9]/.test(value)) score++;

    if (value.length === 0) {
        strengthIndicator.style.width = "0";
        strengthIndicator.style.background = "transparent";
        strengthText.textContent = "Use at least 8 characters";
    } else if (score <= 2) {
        strengthIndicator.style.width = "25%";
        strengthIndicator.style.background = "#e74c3c";
        strengthText.textContent = "Weak password";
    } else if (score <= 4) {
        strengthIndicator.style.width = "65%";
        strengthIndicator.style.background = "#f39c12";
        strengthText.textContent = "Medium password";
    } else {
        strengthIndicator.style.width = "100%";
        strengthIndicator.style.background = "#16a34a";
        strengthText.textContent = "Strong password";
    }
});

// ==================================
// LIVE PASSWORD MATCH CHECK
// ==================================

const confirmPasswordMessage = document.getElementById(
    "confirmPasswordMessage"
);

function checkPasswordMatch() {
    const originalPassword = password.value;
    const confirmValue = confirmPassword.value;

    if (confirmValue.length === 0) {
        confirmPasswordMessage.textContent = "";
        confirmPasswordMessage.className = "password-match-message";
        return;
    }

    if (originalPassword === confirmValue) {
        confirmPasswordMessage.textContent = "✓ Passwords match";
        confirmPasswordMessage.className =
            "password-match-message success";
    } else {
        confirmPasswordMessage.textContent = "✕ Passwords do not match";
        confirmPasswordMessage.className =
            "password-match-message error";
    }
}

confirmPassword.addEventListener("input", checkPasswordMatch);
password.addEventListener("input", checkPasswordMatch);

// ==================================
// MESSAGE FUNCTION
// ==================================

function showMessage(text, type) {
    message.textContent = text;
    message.className = "message " + type;
}

// ==================================
// REGISTRATION FORM VALIDATION
// ==================================

registerForm.addEventListener("submit", function (event) {
    event.preventDefault();

    const nameValue = fullName.value.trim();
    const emailValue = email.value.trim();
    const passwordValue = password.value;
    const confirmValue = confirmPassword.value;

    // Check empty fields
    if (
        !nameValue ||
        !emailValue ||
        !passwordValue ||
        !confirmValue
    ) {
        showMessage("Please fill in all the fields.", "error");
        return;
    }

    // Validate full name
    // Allows letters, spaces and full stops only
    const namePattern = /^[A-Za-z]+(?:[ .][A-Za-z]+)*\.?$/;

    if (!namePattern.test(nameValue)) {
        showMessage(
            "Name can contain only letters, spaces and full stops.",
            "error"
        );
        return;
    }

    // Validate email
   const emailPattern = /^[A-Za-z0-9._%+-]+@[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z][A-Za-z0-9-]*)*\.[A-Za-z]{2,}$/;
    if (!emailPattern.test(emailValue)) {
        showMessage(
            "Please enter a valid email address.",
            "error"
        );
        return;
    }

    // Check password length
    if (passwordValue.length < 8) {
        showMessage(
            "Password must contain at least 8 characters.",
            "error"
        );
        return;
    }

    // Check password requirements
    const strongPassword =
        /[A-Z]/.test(passwordValue) &&
        /[a-z]/.test(passwordValue) &&
        /[0-9]/.test(passwordValue) &&
        /[^A-Za-z0-9]/.test(passwordValue);

    if (!strongPassword) {
        showMessage(
            "Use uppercase, lowercase, a number and a special character.",
            "error"
        );
        return;
    }

    // Check matching passwords
    if (passwordValue !== confirmValue) {
        showMessage(
            "Passwords do not match. Please try again.",
            "error"
        );
        return;
    }

    // Frontend validation completed
    showMessage(
        "Details validated! Account creation will be available after backend connection.",
        "success"
    );
});
