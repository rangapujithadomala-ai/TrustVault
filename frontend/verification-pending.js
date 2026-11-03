
document.addEventListener("DOMContentLoaded", function () {

    const emailDisplay = document.getElementById("email-display");
    const resendButton = document.getElementById("resend-button");
    const resendMessage = document.getElementById("resend-message");

    // Get registered email from the URL
    const params = new URLSearchParams(window.location.search);
    const email = params.get("email");

    if (email) {
        emailDisplay.textContent = email;
    }

    // Temporary frontend demonstration
    resendButton.addEventListener("click", function () {

        resendMessage.textContent =
            "Resend functionality will be available after backend connection.";

    });

});
