// =====================================================
// Shubham Kumar Portfolio — Account & Auth
//
// Sign up / Sign in / session all talk to the real Flask + MySQL
// backend in /server (JWT-based auth). Once signed in, the nav shows
// a small user chip with a dropdown linking to the full dashboard
// (dashboard.html) and, for the admin account, the admin panel
// (admin.html).
// =====================================================

// Point this at your backend. Locally it's the Flask dev server;
// once you deploy the backend (Render/Railway/etc.), replace the
// second URL with your real deployed API address.
const SKP_API_BASE =
    (location.hostname === "127.0.0.1" || location.hostname === "localhost")
        ? "http://127.0.0.1:5000/api"
        : "https://YOUR-BACKEND-URL-HERE.onrender.com/api";

const SKP_TOKEN_KEY = "skp_token";
const SKP_USER_CACHE_KEY = "skp_user_cache";

// -----------------------------------------------------
// Backend API helper
// Password hashing happens server-side (server/utils/security.py).
// In production this MUST be served over HTTPS so the password is
// encrypted in transit (Render/Railway/Vercel all give you HTTPS by
// default).
// -----------------------------------------------------

async function skpApiRequest(path, { method = "GET", body, auth = false, isForm = false } = {}) {
    const headers = {};
    if (!isForm) headers["Content-Type"] = "application/json";
    if (auth) {
        const token = localStorage.getItem(SKP_TOKEN_KEY);
        if (token) headers.Authorization = "Bearer " + token;
    }

    let res;
    try {
        res = await fetch(SKP_API_BASE + path, {
            method,
            headers,
            body: isForm ? body : (body ? JSON.stringify(body) : undefined),
        });
    } catch (err) {
        throw new Error("Could not reach the server. Please check your connection and try again.");
    }

    let data = {};
    try { data = await res.json(); } catch (err) { /* empty body */ }

    if (!res.ok) {
        throw new Error(data.error || "Something went wrong. Please try again.");
    }
    return data;
}

// Exposed globally so dashboard.html / admin.html (separate pages,
// separate <script> files) can reuse the exact same request helper
// and session storage instead of duplicating it.
window.skpApiRequest = skpApiRequest;
window.SKP_TOKEN_KEY = SKP_TOKEN_KEY;
window.SKP_USER_CACHE_KEY = SKP_USER_CACHE_KEY;

function skpMapUser(rawUser) {
    return {
        id: rawUser.id,
        name: rawUser.name,
        username: rawUser.username || null,
        email: rawUser.email,
        profile_photo: rawUser.profile_photo || null,
        cover_photo: rawUser.cover_photo || null,
        bio: rawUser.bio || "",
        resume: rawUser.resume || null,
        certificate: rawUser.certificate || null,
        role: rawUser.role || "user",
        theme: rawUser.theme || "dark",
        profile_visibility: rawUser.profile_visibility || "public",
        notify_email: rawUser.notify_email !== false,
        notify_chat: rawUser.notify_chat !== false,
        createdAt: rawUser.created_at,
    };
}
window.skpMapUser = skpMapUser;

function skpSaveSession(token, user) {
    localStorage.setItem(SKP_TOKEN_KEY, token);
    localStorage.setItem(SKP_USER_CACHE_KEY, JSON.stringify(user));
}

// -----------------------------------------------------
// Validation
// -----------------------------------------------------

function skpIsValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// -----------------------------------------------------
// Auth actions — talk to the Flask + MySQL backend
// -----------------------------------------------------

async function skpSignUp({ name, email, password, confirm }) {
    name = (name || "").trim();
    email = (email || "").trim();

    // Client-side checks give instant feedback; the backend re-validates
    // everything too (never trust the client).
    if (name.length < 2) throw new Error("Please enter your full name.");
    if (!skpIsValidEmail(email)) throw new Error("Please enter a valid email address.");
    if (!password || password.length < 6) throw new Error("Password must be at least 6 characters.");
    if (password !== confirm) throw new Error("Passwords do not match.");

    const data = await skpApiRequest("/auth/signup", {
        method: "POST",
        body: { name, email, password },
    });

    const user = skpMapUser(data.user);
    skpSaveSession(data.token, user);
    return user;
}

async function skpSignIn({ email, password }) {
    email = (email || "").trim();
    if (!skpIsValidEmail(email)) throw new Error("Please enter a valid email address.");
    if (!password) throw new Error("Please enter your password.");

    const data = await skpApiRequest("/auth/login", {
        method: "POST",
        body: { email, password },
    });

    const user = skpMapUser(data.user);
    skpSaveSession(data.token, user);
    return user;
}

function skpSignOut() {
    localStorage.removeItem(SKP_TOKEN_KEY);
    localStorage.removeItem(SKP_USER_CACHE_KEY);
}
window.skpSignOut = skpSignOut;

function skpGetSessionUser() {
    const raw = localStorage.getItem(SKP_USER_CACHE_KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (err) { return null; }
}
window.skpGetSessionUser = skpGetSessionUser;

// Confirms the cached session is still valid with the backend (token
// could have expired, the account could have been deleted or banned).
// Called once on page load; signs the user out quietly if the token no
// longer checks out.
async function skpVerifySession() {
    const token = localStorage.getItem(SKP_TOKEN_KEY);
    if (!token) return null;
    try {
        const data = await skpApiRequest("/auth/me", { auth: true });
        const user = skpMapUser(data.user);
        localStorage.setItem(SKP_USER_CACHE_KEY, JSON.stringify(user));
        return user;
    } catch (err) {
        skpSignOut();
        return null;
    }
}
window.skpVerifySession = skpVerifySession;

// -----------------------------------------------------
// DOM / UI wiring
// -----------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {

    const signInOverlay = document.getElementById("signInOverlay");
    const signInClose = document.getElementById("signInClose");

    const authTabs = document.querySelectorAll(".auth-tab");
    const authForms = document.querySelectorAll(".auth-form");
    const authAlert = document.getElementById("authAlert");

    const signInForm = document.getElementById("signInForm");
    const signUpForm = document.getElementById("signUpForm");
    const forgotLink = document.getElementById("forgotPasswordLink");

    function closeMobileNav() {
        const navMenu = document.getElementById("navMenu");
        const menuToggle = document.getElementById("menuToggle");
        if (navMenu) navMenu.classList.remove("active");
        if (menuToggle) {
            const icon = menuToggle.querySelector("i");
            if (icon) {
                icon.classList.add("fa-bars");
                icon.classList.remove("fa-xmark");
            }
        }
    }

    function openOverlay(el) { if (el) el.classList.add("active"); }
    function closeOverlay(el) { if (el) el.classList.remove("active"); }

    function showAlert(el, type, text) {
        if (!el) return;
        el.textContent = text;
        el.className = "auth-alert show " + type;
        if (type === "success") {
            setTimeout(() => { el.className = "auth-alert"; }, 4000);
        }
    }

    function clearAlert(el) {
        if (!el) return;
        el.className = "auth-alert";
        el.textContent = "";
    }

    function getInitials(name) {
        return (name || "?")
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .map((p) => p[0].toUpperCase())
            .join("");
    }

    // ---------------- Nav bar state ----------------

    function bindSignInButton(btn) {
        btn.addEventListener("click", () => {
            closeMobileNav();
            switchAuthTab("signin");
            clearAlert(authAlert);
            openOverlay(signInOverlay);
        });
    }

    function closeAllDropdowns() {
        document.querySelectorAll(".user-dropdown.open").forEach((d) => d.classList.remove("open"));
    }
    document.addEventListener("click", closeAllDropdowns);

    function renderNavAuthState() {
        const user = skpGetSessionUser();
        const navItem = document.querySelector(".nav-item .signin-button, .nav-item .user-chip-wrap");
        if (!navItem) return;

        if (user) {
            const wrap = document.createElement("div");
            wrap.className = "user-chip-wrap";

            const chip = document.createElement("button");
            chip.className = "user-chip";
            chip.id = "userChip";
            chip.type = "button";
            chip.innerHTML =
                '<span class="user-chip-avatar">' + getInitials(user.name) + "</span>" +
                '<span class="user-chip-name">' + user.name.split(" ")[0] + "</span>" +
                '<i class="fa-solid fa-chevron-down user-chip-caret"></i>';

            const dropdown = document.createElement("div");
            dropdown.className = "user-dropdown";
            dropdown.innerHTML =
                '<a href="dashboard.html" class="user-dropdown-item"><i class="fa-solid fa-gauge"></i> Dashboard</a>' +
                (user.role === "admin"
                    ? '<a href="admin.html" class="user-dropdown-item"><i class="fa-solid fa-shield-halved"></i> Admin Panel</a>'
                    : "") +
                '<button type="button" class="user-dropdown-item danger" id="navLogoutBtn"><i class="fa-solid fa-right-from-bracket"></i> Sign Out</button>';

            chip.addEventListener("click", (e) => {
                e.stopPropagation();
                closeMobileNav();
                const willOpen = !dropdown.classList.contains("open");
                closeAllDropdowns();
                if (willOpen) dropdown.classList.add("open");
            });
            dropdown.addEventListener("click", (e) => e.stopPropagation());

            wrap.appendChild(chip);
            wrap.appendChild(dropdown);
            navItem.replaceWith(wrap);

            wrap.querySelector("#navLogoutBtn").addEventListener("click", () => {
                skpSignOut();
                closeAllDropdowns();
                renderNavAuthState();
            });
        } else if (!navItem.classList.contains("signin-button") || !navItem.dataset.bound) {
            const fresh = document.createElement("button");
            fresh.className = "signin-button";
            fresh.id = "signInBtn";
            fresh.type = "button";
            fresh.textContent = "Sign In";
            fresh.dataset.bound = "1";
            bindSignInButton(fresh);
            navItem.replaceWith(fresh);
        }
    }
    window.skpRenderNavAuthState = renderNavAuthState;

    // ---------------- Auth tabs ----------------

    function switchAuthTab(mode) {
        authTabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === mode));
        authForms.forEach((f) => f.classList.toggle("active", f.dataset.mode === mode));
        clearAlert(authAlert);
    }

    authTabs.forEach((tab) => {
        tab.addEventListener("click", () => switchAuthTab(tab.dataset.tab));
    });

    if (signInClose) signInClose.addEventListener("click", () => closeOverlay(signInOverlay));
    if (signInOverlay) {
        signInOverlay.addEventListener("click", (e) => {
            if (e.target === signInOverlay) closeOverlay(signInOverlay);
        });
    }
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeOverlay(signInOverlay);
    });

    if (forgotLink) {
        forgotLink.addEventListener("click", (e) => {
            e.preventDefault();
            window.location.href = "forgot-password.html";
        });
    }

    // ---------------- Sign in / Sign up forms ----------------

    if (signInForm) {
        signInForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(authAlert);
            const submitBtn = signInForm.querySelector(".signin-submit");
            const original = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = "<span>Signing in...</span>";

            try {
                const data = new FormData(signInForm);
                const user = await skpSignIn({
                    email: data.get("email"),
                    password: data.get("password"),
                });
                showAlert(authAlert, "success", "Welcome back, " + user.name.split(" ")[0] + "!");
                renderNavAuthState();
                setTimeout(() => {
                    closeOverlay(signInOverlay);
                    signInForm.reset();
                }, 700);
            } catch (err) {
                showAlert(authAlert, "error", err.message);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = original;
            }
        });
    }

    if (signUpForm) {
        signUpForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(authAlert);
            const submitBtn = signUpForm.querySelector(".signin-submit");
            const original = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = "<span>Creating account...</span>";

            try {
                const data = new FormData(signUpForm);
                const user = await skpSignUp({
                    name: data.get("name"),
                    email: data.get("email"),
                    password: data.get("password"),
                    confirm: data.get("confirm"),
                });
                showAlert(authAlert, "success", "Account created! Welcome, " + user.name.split(" ")[0] + ".");
                renderNavAuthState();
                setTimeout(() => {
                    closeOverlay(signInOverlay);
                    signUpForm.reset();
                }, 700);
            } catch (err) {
                showAlert(authAlert, "error", err.message);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = original;
            }
        });
    }

    // ---------------- Init ----------------

    const initialBtn = document.getElementById("signInBtn");
    if (initialBtn && !initialBtn.dataset.bound) {
        initialBtn.dataset.bound = "1";
        bindSignInButton(initialBtn);
    }

    // Render instantly from the cached user (no flicker/wait), then quietly
    // confirm with the backend that the token is still valid — if it has
    // expired, the account was deleted, or the account got banned, this
    // signs the user out and re-renders the "Sign In" button.
    renderNavAuthState();
    skpVerifySession().then(() => renderNavAuthState());
});
