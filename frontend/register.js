
document.addEventListener("DOMContentLoaded", function () {

    // Form elements
    const registerForm = document.getElementById("registerForm");

    const fullNameInput = document.getElementById("fullName");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const confirmPasswordInput = document.getElementById("confirmPassword");

    const togglePassword = document.getElementById("togglePassword");
    const toggleConfirmPassword = document.getElementById("toggleConfirmPassword");

    const message = document.getElementById("message");
    const submitButton = document.getElementById("submitButton");
const passwordMatchMessage = document.getElementById("confirmPasswordMessage");
    const strengthBar = document.querySelector(".strength-bar span");
    const strengthText = document.querySelector(".password-strength p");

    if (!registerForm) {
        console.error("Registration form not found.");
        return;
    }

    // Display messages
    function showMessage(text, type) {
        message.textContent = text;
        message.className = "message " + type;
    }

    // Show/hide password
    function setupPasswordToggle(button, input) {

        if (!button || !input) return;

        button.addEventListener("click", function () {

            const isPassword = input.type === "password";

            input.type = isPassword ? "text" : "password";

            button.setAttribute(
                "aria-label",
                isPassword ? "Hide password" : "Show password"
            );
        });
    }

    setupPasswordToggle(togglePassword, passwordInput);
    setupPasswordToggle(toggleConfirmPassword, confirmPasswordInput);


    // Password strength calculation
    function calculatePasswordStrength(password) {

        let strength = 0;

        if (password.length >= 8) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[a-z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^A-Za-z0-9]/.test(password)) strength++;

        return strength;
    }


    // Update password strength indicator
    function updatePasswordStrength() {

        const password = passwordInput.value;
        const strength = calculatePasswordStrength(password);

        const strengthLabels = [
            "Enter a password",
            "Very weak",
            "Weak",
            "Fair",
            "Good",
            "Strong"
        ];

        const strengthColors = [
            "#e9eaf0",
            "#dc3545",
            "#fd7e14",
            "#ffc107",
            "#0d9488",
            "#16a34a"
        ];

        if (strengthBar) {
            strengthBar.style.width = (strength * 20) + "%";
            strengthBar.style.background = strengthColors[strength];
        }

        if (strengthText) {
            strengthText.textContent = strengthLabels[strength];
        }
    }


    passwordInput.addEventListener("input", function () {
        updatePasswordStrength();
        checkPasswordMatch();
    });


    // Check password confirmation
    function checkPasswordMatch() {

        if (!confirmPasswordInput.value) {

            if (passwordMatchMessage) {
                passwordMatchMessage.textContent = "";
                passwordMatchMessage.className = "password-match-message";
            }

            return false;
        }

        if (passwordInput.value === confirmPasswordInput.value) {

            if (passwordMatchMessage) {
                passwordMatchMessage.textContent = "Passwords match.";
                passwordMatchMessage.className =
                    "password-match-message success";
            }

            return true;

        } else {

            if (passwordMatchMessage) {
                passwordMatchMessage.textContent = "Passwords do not match.";
                passwordMatchMessage.className =
                    "password-match-message error";
            }

            return false;
        }
    }


    confirmPasswordInput.addEventListener("input", checkPasswordMatch);


    // Registration form submission
    registerForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        message.className = "message";

        const name = fullNameInput.value.trim();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        const namePattern = /^[A-Za-z]+(?:[ .'-][A-Za-z]+)*$/;
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        // Name validation
        if (!name) {
            showMessage("Please enter your full name.", "error");
            fullNameInput.focus();
            return;
        }

        if (!namePattern.test(name)) {
            showMessage("Please enter a valid full name.", "error");
            fullNameInput.focus();
            return;
        }

        // Email validation
        if (!email) {
            showMessage("Please enter your email address.", "error");
            emailInput.focus();
            return;
        }

        if (!emailPattern.test(email)) {
            showMessage("Please enter a valid email address.", "error");
            emailInput.focus();
            return;
        }

        // Password validation
        if (
            password.length < 8 ||
            !/[A-Z]/.test(password) ||
            !/[a-z]/.test(password) ||
            !/[0-9]/.test(password) ||
            !/[^A-Za-z0-9]/.test(password)
        ) {
            showMessage(
                "Password must contain at least 8 characters, uppercase, lowercase, number and special character.",
                "error"
            );

            passwordInput.focus();
            return;
        }

        // Confirm password validation
        if (!confirmPassword) {
            showMessage("Please confirm your password.", "error");
            confirmPasswordInput.focus();
            return;
        }

        if (password !== confirmPassword) {
            showMessage("Passwords do not match.", "error");
            confirmPasswordInput.focus();
            return;
        }

        // Get CSRF token
        const csrfToken = document.querySelector(
            'meta[name="csrf-token"]'
        )?.content;

        if (!csrfToken) {
            showMessage(
                "Security token missing. Please refresh the page.",
                "error"
            );
            return;
        }

        // Disable submit button
        const originalButtonText = submitButton.textContent;

        submitButton.disabled = true;
        submitButton.textContent = "Creating Account...";

        try {

            // Send registration request to Flask
            const response = await fetch("/auth/register", {

                method: "POST",

                credentials: "same-origin",

                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },

                body: JSON.stringify({
                    name: name,
                    email: email,
                    password: password,
                    confirm_password: confirmPassword
                })

            });

            const data = await response.json();

            if (!response.ok) {

                showMessage(
                    data.error || data.message || "Registration failed. Please try again.",
                    "error"
                );

                return;
            }

            showMessage(
                data.message || "Account created. Please check your email for verification instructions.",
                "success"
            );

            if (data.redirect) {
                window.location.href = data.redirect;
            } else {
                window.location.href = "/verification-pending.html?email=" + encodeURIComponent(email);
            }

        } catch (error) {

            console.error("Registration error:", error);

            showMessage(
                "Unable to connect to the server. Please try again.",
                "error"
            );

        } finally {

            submitButton.disabled = false;
            submitButton.textContent = originalButtonText;

        }

    });

});
