
document.addEventListener("DOMContentLoaded", function () {
    const statusContainer = document.getElementById("verification-status");
    const verificationIcon = document.querySelector(".verification-icon");
    const verificationMessage = document.querySelector(".verification-message");

    // Temporary frontend demonstration
    // Actual verification will be handled by Flask using the email token.

    const params = new URLSearchParams(window.location.search);
    const status = params.get("status");

    if (status === "success") {
        verificationIcon.textContent = "✓";
        verificationIcon.style.background = "#e6f7ed";
        verificationIcon.style.color = "#16834a";

        verificationMessage.textContent = "Your email has been verified successfully.";

        statusContainer.textContent = "Your TrustVault account is now ready to use.";
    } 
    else if (status === "expired") {
        verificationIcon.textContent = "!";
        verificationIcon.style.background = "#fff4e5";
        verificationIcon.style.color = "#d97706";

        verificationMessage.textContent = "Your verification link has expired.";

        statusContainer.textContent = "Please request a new verification link.";
    } 
    else if (status === "invalid") {
        verificationIcon.textContent = "!";
        verificationIcon.style.background = "#fdecec";
        verificationIcon.style.color = "#dc2626";

        verificationMessage.textContent = "This verification link is invalid.";

        statusContainer.textContent = "Please check your email for the correct link.";
    }
});
