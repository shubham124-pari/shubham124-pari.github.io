const API_BASE = "http://127.0.0.1:5000/api/auth";

const overlay = document.getElementById("signInOverlay");
const openBtn = document.getElementById("signInBtn");
const closeBtn = document.getElementById("signInClose");
const tabSignIn = document.getElementById("tabSignIn");
const tabSignUp = document.getElementById("tabSignUp");
const signInForm = document.getElementById("signInForm");
const signUpForm = document.getElementById("signUpForm");
const alertBox = document.getElementById("authAlert");
const googleBtn = document.getElementById("googleSignInBtn");

function showAlert(msg, isError = true) {
  if (!alertBox) return;
  alertBox.textContent = msg;
  alertBox.style.color = isError ? "#ff5c5c" : "#3ddc84";
}

function saveSession(token, user) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
  window.location.reload();
}

if (openBtn && overlay) openBtn.addEventListener("click", () => overlay.classList.add("active"));
if (closeBtn && overlay) closeBtn.addEventListener("click", () => overlay.classList.remove("active"));

if (tabSignIn && tabSignUp && signInForm && signUpForm) {
  tabSignIn.addEventListener("click", () => {
    tabSignIn.classList.add("active");
    tabSignUp.classList.remove("active");
    signInForm.classList.add("active");
    signUpForm.classList.remove("active");
  });
  tabSignUp.addEventListener("click", () => {
    tabSignUp.classList.add("active");
    tabSignIn.classList.remove("active");
    signUpForm.classList.add("active");
    signInForm.classList.remove("active");
  });
}

if (signInForm) {
  signInForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(signInForm);
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: fd.get("email"), password: fd.get("password") }),
      });
      const data = await res.json();
      if (!res.ok) return showAlert(data.error || "Login failed.");
      saveSession(data.token, data.user);
    } catch (err) {
      showAlert("Server se connect nahi ho paya.");
    }
  });
}

if (signUpForm) {
  signUpForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(signUpForm);
    if (fd.get("password") !== fd.get("confirm")) return showAlert("Passwords match nahi kar rahe.");
    try {
      const res = await fetch(`${API_BASE}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: fd.get("name"),
          email: fd.get("email"),
          password: fd.get("password"),
        }),
      });
      const data = await res.json();
      if (!res.ok) return showAlert(data.error || "Signup failed.");
      saveSession(data.token, data.user);
    } catch (err) {
      showAlert("Server se connect nahi ho paya.");
    }
  });
}

// ---------------- Google Sign-In ----------------
async function handleGoogleCredential(response) {
  try {
    const res = await fetch(`${API_BASE}/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential: response.credential }),
    });
    const data = await res.json();
    if (!res.ok) return showAlert(data.error || "Google sign-in failed.");
    saveSession(data.token, data.user);
  } catch (err) {
    showAlert("Server se connect nahi ho paya.");
  }
}

window.addEventListener("load", () => {
  const clientId = document.querySelector('meta[name="google-client-id"]')?.content;
  if (window.google && clientId && googleBtn) {
    google.accounts.id.initialize({
      client_id: clientId,
      callback: handleGoogleCredential,
    });
    googleBtn.addEventListener("click", () => {
      google.accounts.id.prompt();
    });
  }
});