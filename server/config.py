import os
from dotenv import load_dotenv

# Load variables from server/.env into the environment
load_dotenv()


class Config:
    """Central place for every setting the app needs.
    Everything is read from environment variables (.env file)
    so real secrets never get hard-coded or committed to GitHub.
    """

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "shubham_portfolio")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "24"))

    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")

    # Optional: if unset, contact messages are still saved to MySQL but no
    # email notification is sent (mirrors the frontend's existing behavior
    # in assets/js/auth.js when its own WEB3FORMS_ACCESS_KEY is left blank).
    WEB3FORMS_ACCESS_KEY = os.getenv("WEB3FORMS_ACCESS_KEY", "")

    # Preferred way to send password-reset emails: Brevo's HTTPS API
    # (https://api.brevo.com). Works everywhere, including hosts like
    # Render's free tier that block outbound SMTP ports. Get a free key
    # at https://app.brevo.com -> profile icon -> SMTP & API -> API Keys.
    # BREVO_SENDER_EMAIL must be a "verified sender" in your Brevo account
    # (Senders, Domains & Dedicated IPs -> Senders -> Add a sender).
    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
    BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
    BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Shubham Kumar Portfolio")

    # Fallback: plain SMTP. Works fine for local development, but most
    # free cloud hosts (Render free tier included) block outbound SMTP
    # ports — use BREVO_API_KEY above for anything deployed. If neither
    # Brevo nor SMTP is configured, reset links are printed to the server
    # console instead (fine for local dev/testing). For Gmail: use an
    # "app password", not your normal password (Google Account ->
    # Security -> App passwords).
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "")

    # Used to build the link inside password-reset emails, e.g.
    # "https://shubham124-pari.github.io/reset-password.html"
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")

    # AI_PROVIDER = "gemini" | "openai". Both are called via plain HTTPS
    # requests (urllib, stdlib only) so no extra pip package is required.
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    # First account to sign up with this email is auto-promoted to admin
    # on signup — set this in .env to your own email before first run.
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

    @classmethod
    def validate(cls):
        """Fail loudly at startup instead of quietly misbehaving later."""
        if cls.FLASK_ENV == "production" and cls.JWT_SECRET_KEY == "dev-secret-change-me":
            raise RuntimeError(
                "JWT_SECRET_KEY is still the default value. "
                "Set a real secret in server/.env before deploying."
            )
