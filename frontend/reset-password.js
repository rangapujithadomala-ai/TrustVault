
// ==================================
// GET HTML ELEMENTS
// ==================================

const resetPasswordForm = document.getElementById("resetPasswordForm");

const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirmPassword");

const togglePassword = document.getElementById("togglePassword");
const toggleConfirmPassword = document.getElementById("toggleConfirmPassword");

const strengthIndicator = document.getElementById("strengthIndicator");
const strengthText = document.getElementById("strengthText");

const confirmPasswordMessage = document.getElementById(
    "confirmPasswordMessage"
);

const message = document.getElementById("message");

// ==================================
// PASSWORD SHOW / HIDE
// ==================================

function setupPasswordToggle(button, input, fieldName) {

    button.addEventListener("click", function () {

        const isHidden = input.type === "password";

        input.type = isHidden ? "text" : "password";

        button.setAttribute(
            "aria-label",
            isHidden ? "Hide " + fieldName : "Show " + fieldName
        );

        button.setAttribute(
            "aria-pressed",
            isHidden ? "true" : "false"
        );

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

    checkPasswordMatch();

});

// ==================================
// LIVE PASSWORD MATCH CHECK
// ==================================

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

// ==================================
// MESSAGE FUNCTION
// ==================================

function showMessage(text, type) {

    message.textContent = text;
    message.className = "message " + type;

}

// ==================================
// RESET PASSWORD VALIDATION
// ==================================

resetPasswordForm.addEventListener("submit", function (event) {

    event.preventDefault();

    const passwordValue = password.value;
    const confirmValue = confirmPassword.value;

    // Check empty fields
    if (!passwordValue || !confirmValue) {

        showMessage("Please fill in both password fields.", "error");
        return;

    }

    // Check minimum password length
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

    // Backend integration pending
    showMessage(
        "Password validated. Actual reset requires backend verification.",
        "success"
    );

});
