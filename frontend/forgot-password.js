
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

    // Backend connection will send the actual reset link
    showMessage(
        "Email format validated. Password reset will be available after backend connection.",
        "success"
    );

});
