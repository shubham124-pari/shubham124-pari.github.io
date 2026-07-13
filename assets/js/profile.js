// =====================================================
// profile.html logic
// Loads the profile named in ?u=<username>. Works for signed-out
// visitors too (skpApiRequest with auth:true just omits the header
// when there's no token — the backend's optional_token decorator
// handles the rest).
// =====================================================

document.addEventListener("DOMContentLoaded", async () => {

    const shell = document.getElementById("profileShell");
    const guard = document.getElementById("profileGuard");
    const guardTitle = document.getElementById("profileGuardTitle");
    const guardText = document.getElementById("profileGuardText");

    const profileAvatar = document.getElementById("profileAvatar");
    const profileName = document.getElementById("profileName");
    const profileHandle = document.getElementById("profileHandle");
    const profileCounts = document.getElementById("profileCounts");
    const profileBio = document.getElementById("profileBio");
    const profileActions = document.getElementById("profileActions");
    const profileActionAlert = document.getElementById("profileActionAlert");

    const ownerSettingsPanel = document.getElementById("ownerSettingsPanel");
    const profileSettingsForm = document.getElementById("profileSettingsForm");
    const usernameInput = document.getElementById("usernameInput");
    const visibilityInput = document.getElementById("visibilityInput");

    const profilePostsList = document.getElementById("profilePostsList");
    const profilePostsEmpty = document.getElementById("profilePostsEmpty");

    function getInitials(name) {
        return (name || "?").trim().split(/\s+/).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str == null ? "" : String(str);
        return div.innerHTML;
    }

    function formatDate(iso) {
        if (!iso) return "";
        try {
            return new Date(iso).toLocaleString(undefined, {
                year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
            });
        } catch (e) {
            return "";
        }
    }

    function fileUrl(relativePath) {
        if (!relativePath) return null;
        const origin = SKP_API_BASE.replace(/\/api\/?$/, "");
        return origin + relativePath;
    }

    function showAlert(el, type, text) {
        if (!el) return;
        el.textContent = text;
        el.className = "auth-alert show " + type;
        if (type === "success") setTimeout(() => { el.className = "auth-alert"; }, 4000);
    }

    const VISIBILITY_LABEL = {
        public: "🌍 Public",
        connections_only: "🤝 Connections only",
        private: "🔒 Only me",
    };

    const params = new URLSearchParams(window.location.search);
    const username = (params.get("u") || "").trim().toLowerCase();

    if (!username) {
        guard.style.display = "block";
        guardTitle.textContent = "No profile specified";
        guardText.textContent = "Open this page as profile.html?u=<username>.";
        return;
    }

    let profile = null;
    let viewer = null;

    async function boot() {
        viewer = skpGetSessionUser();
        if (viewer) viewer = await skpVerifySession(); // refresh, in case it changed

        try {
            const data = await skpApiRequest(`/social/profile/${encodeURIComponent(username)}`, { auth: true });
            profile = data.profile;
        } catch (err) {
            guard.style.display = "block";
            guardTitle.textContent = "This profile isn't available";
            guardText.textContent = err.message || "It may be private, or the username doesn't exist.";
            return;
        }

        render();
        shell.style.display = "block";
        loadPosts();
    }

    function render() {
        profileAvatar.textContent = profile.profile_photo ? "" : getInitials(profile.name);
        if (profile.profile_photo) {
            profileAvatar.innerHTML = `<img src="${escapeHtml(fileUrl(profile.profile_photo))}" alt="" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
        }
        profileName.textContent = profile.name;
        profileHandle.textContent = (profile.username ? "@" + profile.username : "") +
            "  ·  " + (VISIBILITY_LABEL[profile.profile_visibility] || profile.profile_visibility);
        profileCounts.textContent = `${profile.followers_count} followers · ${profile.following_count} following`;
        profileBio.textContent = profile.bio || "";

        renderActions();

        if (profile.is_owner) {
            ownerSettingsPanel.style.display = "block";
            usernameInput.value = profile.username || "";
            visibilityInput.value = profile.profile_visibility || "public";
        }
    }

    function renderActions() {
        profileActions.innerHTML = "";
        if (profile.is_owner) {
            const editLink = document.createElement("a");
            editLink.href = "dashboard.html";
            editLink.className = "signin-option";
            editLink.style.maxWidth = "200px";
            editLink.textContent = "Edit profile in Dashboard";
            profileActions.appendChild(editLink);
            return;
        }

        if (!viewer) {
            const hint = document.createElement("p");
            hint.className = "account-meta";
            hint.style.textAlign = "left";
            hint.textContent = "Sign in to follow or connect with this person.";
            profileActions.appendChild(hint);
            return;
        }

        const followBtn = document.createElement("button");
        followBtn.type = "button";
        followBtn.className = "signin-option";
        followBtn.style.maxWidth = "160px";
        followBtn.textContent = profile.is_following ? "Following" : "Follow";
        followBtn.addEventListener("click", async () => {
            try {
                await skpApiRequest(`/social/follow/${profile.id}`, {
                    method: profile.is_following ? "DELETE" : "POST", auth: true,
                });
                profile.is_following = !profile.is_following;
                followBtn.textContent = profile.is_following ? "Following" : "Follow";
            } catch (err) {
                showAlert(profileActionAlert, "error", err.message);
            }
        });
        profileActions.appendChild(followBtn);

        const connectBtn = document.createElement("button");
        connectBtn.type = "button";
        connectBtn.className = "signin-option";
        connectBtn.style.maxWidth = "160px";
        connectBtn.textContent = profile.is_connected ? "Connected" : "Connect";
        connectBtn.disabled = !!profile.is_connected;
        connectBtn.addEventListener("click", async () => {
            try {
                await skpApiRequest(`/social/connections/request/${profile.id}`, { method: "POST", auth: true, body: {} });
                connectBtn.textContent = "Requested";
                connectBtn.disabled = true;
            } catch (err) {
                showAlert(profileActionAlert, "error", err.message);
            }
        });
        profileActions.appendChild(connectBtn);
    }

    // ---------------- owner privacy settings ----------------

    if (profileSettingsForm) {
        profileSettingsForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const body = {};
            if (usernameInput.value.trim()) body.username = usernameInput.value.trim().toLowerCase();
            body.profile_visibility = visibilityInput.value;

            try {
                await skpApiRequest("/social/profile/settings", { method: "PUT", auth: true, body });
                showAlert(profileActionAlert, "success", "Saved. Reloading...");
                setTimeout(() => {
                    window.location.href = `profile.html?u=${encodeURIComponent(body.username || username)}`;
                }, 800);
            } catch (err) {
                showAlert(profileActionAlert, "error", err.message);
            }
        });
    }

    // ---------------- posts ----------------

    function renderPostCard(post) {
        const card = document.createElement("div");
        card.className = "post-card";

        const media = post.media_url
            ? (post.post_type === "video"
                ? `<div class="post-card-media"><video src="${escapeHtml(fileUrl(post.media_url))}" controls></video></div>`
                : `<div class="post-card-media"><img src="${escapeHtml(fileUrl(post.media_url))}" alt=""></div>`)
            : "";

        card.innerHTML = `
            <div class="post-card-meta" style="margin-bottom:8px;">${formatDate(post.created_at)}${post.is_edited ? " · edited" : ""} · ${VISIBILITY_LABEL[post.visibility] || post.visibility}</div>
            <div class="post-card-content">${escapeHtml(post.content || "")}</div>
            ${media}
            <div class="post-card-actions">
                <span><i class="fa-solid fa-heart"></i> ${post.likes_count}</span>
                <span><i class="fa-solid fa-comment"></i> ${post.comments_count}</span>
                <span><i class="fa-solid fa-share"></i> ${post.shares_count}</span>
            </div>
        `;
        return card;
    }

    async function loadPosts() {
        try {
            const data = await skpApiRequest(`/posts/user/${encodeURIComponent(username)}`, { auth: true });
            const posts = data.posts || [];
            profilePostsList.innerHTML = "";
            profilePostsEmpty.style.display = posts.length === 0 ? "block" : "none";
            posts.forEach((p) => profilePostsList.appendChild(renderPostCard(p)));
        } catch (err) {
            profilePostsEmpty.textContent = err.message;
            profilePostsEmpty.style.display = "block";
        }
    }

    boot();
});
