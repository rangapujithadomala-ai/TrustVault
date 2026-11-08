
// ==================================
// GET HTML ELEMENTS
// ==================================

const forgotPasswordForm = document.getElementById("forgotPasswordForm");
const emailInput = document.getElementById("email");
const message = document.getElementById("message");

// ==================================
// MESSAGE FUNCTION
// ==================================

function showMessage(text, type) {
    message.textContent = text;
    message.className = "message " + type;
}

// ==================================
// FORGOT PASSWORD VALIDATION
// ==================================

forgotPasswordForm.addEventListener("submit", function (event) {

    event.preventDefault();

    const email = emailInput.value.trim();

    // Check empty email
    if (!email) {
        showMessage("Please enter your email address.", "error");
        return;
    }

    // Validate email format
    const emailPattern = /^[A-Za-z0-9._%+-]+@[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z][A-Za-z0-9-]*)*\.[A-Za-z]{2,}$/;

    if (!emailPattern.test(email)) {
        showMessage("Please enter a valid email address.", "error");
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
    const submitButton = forgotPasswordForm.querySelector('button[type="submit"]');
    if (submitButton) { submitButton.disabled = true; submitButton.textContent = "Sending..."; }
    fetch("/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify({ email })
    }).then(async response => {
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result.error || "Unable to request password reset.");
        showMessage(result.message || "If the account exists, a reset link will be sent.", "success");
    }).catch(error => showMessage(error.message, "error"))
      .finally(() => { if (submitButton) { submitButton.disabled = false; submitButton.textContent = "Send Reset Link"; } });

});
