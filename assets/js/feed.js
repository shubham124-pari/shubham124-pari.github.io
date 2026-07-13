// =====================================================
// feed.html logic
// Relies on globals from auth.js: skpApiRequest, skpMapUser,
// skpGetSessionUser, skpVerifySession, skpSignOut.
// Mirrors dashboard.js conventions (escapeHtml, formatDate, fileUrl,
// showAlert/clearAlert) — kept local here since dashboard.js isn't
// loaded on this page.
// =====================================================

document.addEventListener("DOMContentLoaded", async () => {

    const guard = document.getElementById("dashboardGuard");
    const guardSignInBtn = document.getElementById("dashboardSignInBtn");
    const shell = document.getElementById("feedShell");

    const feedAvatar = document.getElementById("feedAvatar");
    const feedGreeting = document.getElementById("feedGreeting");
    const feedMeta = document.getElementById("feedMeta");

    const tabs = document.querySelectorAll("#feedTabs .account-tab");
    const panels = document.querySelectorAll(".account-panel");

    let currentUser = null;

    // ---------------- helpers (same behavior as dashboard.js) ----------------

    function getInitials(name) {
        return (name || "?").trim().split(/\s+/).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
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

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str == null ? "" : String(str);
        return div.innerHTML;
    }

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

    function fileUrl(relativePath) {
        if (!relativePath) return null;
        const origin = SKP_API_BASE.replace(/\/api\/?$/, "");
        return origin + relativePath;
    }

    const VISIBILITY_LABEL = {
        public: "🌍 Public",
        connections_only: "🤝 Connections only",
        private: "🔒 Only me",
    };

    if (guardSignInBtn) {
        guardSignInBtn.addEventListener("click", () => {
            const btn = document.getElementById("signInBtn");
            if (btn) btn.click();
        });
    }

    // ---------------- guard: must be signed in ----------------

    async function boot() {
        const cached = skpGetSessionUser();
        if (!cached) {
            guard.style.display = "block";
            return;
        }
        const verified = await skpVerifySession();
        if (!verified) {
            guard.style.display = "block";
            return;
        }
        currentUser = verified;
        renderHeader(currentUser);
        shell.style.display = "block";
        loadFeed();
    }

    function renderHeader(user) {
        feedAvatar.textContent = getInitials(user.name);
        feedGreeting.textContent = "Your Feed";
        feedMeta.textContent = "Signed in as " + user.name + (user.username ? " · @" + user.username : "");
    }

    // ---------------- tabs ----------------

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.toggle("active", t === tab));
            const targetId = tab.dataset.ftab + "Panel";
            panels.forEach((p) => p.classList.toggle("active", p.id === targetId));

            if (tab.dataset.ftab === "explore") loadExplore();
            if (tab.dataset.ftab === "requests") loadRequests();
            if (tab.dataset.ftab === "bookmarks") loadBookmarks();
        });
    });

    // ================================================
    // POST CARD RENDERING (shared by feed/explore/bookmarks)
    // ================================================

    function renderPostCard(post, { showOwnerActions = false } = {}) {
        const card = document.createElement("div");
        card.className = "post-card";
        card.dataset.postId = post.id;

        const author = post.author || {};
        const authorName = author.name || (post.user_id === currentUser.id ? currentUser.name : "Unknown");
        const authorUsername = author.username || (post.user_id === currentUser.id ? currentUser.username : null);
        const authorPhoto = author.profile_photo || (post.user_id === currentUser.id ? currentUser.profile_photo : null);
        const profileLink = authorUsername ? `profile.html?u=${encodeURIComponent(authorUsername)}` : "#";

        const avatarInner = authorPhoto
            ? `<img src="${escapeHtml(fileUrl(authorPhoto))}" alt="" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`
            : getInitials(authorName);

        const media = post.media_url
            ? (post.post_type === "video"
                ? `<div class="post-card-media"><video src="${escapeHtml(fileUrl(post.media_url))}" controls></video></div>`
                : `<div class="post-card-media"><img src="${escapeHtml(fileUrl(post.media_url))}" alt=""></div>`)
            : "";

        const isOwner = post.user_id === currentUser.id;

        card.innerHTML = `
            <div class="post-card-header">
                <a class="post-card-avatar" href="${profileLink}">${avatarInner}</a>
                <div>
                    <div><a href="${profileLink}" style="color:#fff;text-decoration:none;font-weight:600;">${escapeHtml(authorName)}</a></div>
                    <div class="post-card-meta">${formatDate(post.created_at)}${post.is_edited ? " · edited" : ""} · ${VISIBILITY_LABEL[post.visibility] || post.visibility}</div>
                </div>
            </div>
            <div class="post-card-content">${escapeHtml(post.content || "")}</div>
            ${media}
            <div class="post-card-actions">
                <button type="button" class="like-btn ${post.liked_by_viewer ? "active" : ""}">
                    <i class="fa-${post.liked_by_viewer ? "solid" : "regular"} fa-heart"></i> <span class="like-count">${post.likes_count}</span>
                </button>
                <button type="button" class="comment-toggle-btn"><i class="fa-regular fa-comment"></i> <span class="comment-count">${post.comments_count}</span></button>
                <button type="button" class="share-btn"><i class="fa-solid fa-share"></i> <span class="share-count">${post.shares_count}</span></button>
                <button type="button" class="bookmark-btn ${post.bookmarked_by_viewer ? "active" : ""}">
                    <i class="fa-${post.bookmarked_by_viewer ? "solid" : "regular"} fa-bookmark"></i>
                </button>
                ${isOwner ? `<button type="button" class="delete-post-btn" style="margin-left:auto;"><i class="fa-solid fa-trash"></i> Delete</button>` : ""}
            </div>
            <div class="post-card-comments">
                <div class="comments-list"></div>
                <form class="post-card-comment-form">
                    <input type="text" placeholder="Write a comment..." maxlength="1000">
                    <button type="submit"><i class="fa-solid fa-paper-plane"></i></button>
                </form>
            </div>
        `;

        // ---- like ----
        card.querySelector(".like-btn").addEventListener("click", async (e) => {
            const btn = e.currentTarget;
            const liked = btn.classList.contains("active");
            try {
                await skpApiRequest(`/posts/${post.id}/like`, { method: liked ? "DELETE" : "POST", auth: true });
                btn.classList.toggle("active", !liked);
                btn.querySelector("i").className = `fa-${!liked ? "solid" : "regular"} fa-heart`;
                const countEl = btn.querySelector(".like-count");
                countEl.textContent = Math.max(0, parseInt(countEl.textContent, 10) + (liked ? -1 : 1));
            } catch (err) {
                alert(err.message);
            }
        });

        // ---- bookmark ----
        card.querySelector(".bookmark-btn").addEventListener("click", async (e) => {
            const btn = e.currentTarget;
            const bookmarked = btn.classList.contains("active");
            try {
                await skpApiRequest(`/posts/${post.id}/bookmark`, { method: bookmarked ? "DELETE" : "POST", auth: true });
                btn.classList.toggle("active", !bookmarked);
                btn.querySelector("i").className = `fa-${!bookmarked ? "solid" : "regular"} fa-bookmark`;
            } catch (err) {
                alert(err.message);
            }
        });

        // ---- share ----
        card.querySelector(".share-btn").addEventListener("click", async (e) => {
            try {
                await skpApiRequest(`/posts/${post.id}/share`, { method: "POST", auth: true, body: {} });
                const countEl = card.querySelector(".share-count");
                countEl.textContent = parseInt(countEl.textContent, 10) + 1;
            } catch (err) {
                alert(err.message);
            }
        });

        // ---- delete (owner only) ----
        const deleteBtn = card.querySelector(".delete-post-btn");
        if (deleteBtn) {
            deleteBtn.addEventListener("click", async () => {
                if (!confirm("Delete this post? This can't be undone.")) return;
                try {
                    await skpApiRequest(`/posts/${post.id}`, { method: "DELETE", auth: true });
                    card.remove();
                } catch (err) {
                    alert(err.message);
                }
            });
        }

        // ---- comments ----
        const commentsBox = card.querySelector(".post-card-comments");
        const commentsList = card.querySelector(".comments-list");
        let commentsLoaded = false;

        async function loadComments() {
            try {
                const data = await skpApiRequest(`/posts/${post.id}/comments`, { auth: true });
                commentsList.innerHTML = (data.comments || []).map((c) => `
                    <div class="post-card-comment">
                        <strong>${escapeHtml(c.author.name)}</strong> ${escapeHtml(c.content)}
                    </div>
                `).join("") || `<p class="account-meta" style="text-align:left;">No comments yet.</p>`;
                commentsLoaded = true;
            } catch (err) {
                commentsList.innerHTML = `<p class="account-meta" style="text-align:left;">${escapeHtml(err.message)}</p>`;
            }
        }

        card.querySelector(".comment-toggle-btn").addEventListener("click", () => {
            commentsBox.classList.toggle("open");
            if (commentsBox.classList.contains("open") && !commentsLoaded) loadComments();
        });

        card.querySelector(".post-card-comment-form").addEventListener("submit", async (e) => {
            e.preventDefault();
            const input = e.currentTarget.querySelector("input");
            const content = input.value.trim();
            if (!content) return;
            try {
                await skpApiRequest(`/posts/${post.id}/comments`, { method: "POST", auth: true, body: { content } });
                input.value = "";
                await loadComments();
                const countEl = card.querySelector(".comment-count");
                countEl.textContent = parseInt(countEl.textContent, 10) + 1;
            } catch (err) {
                alert(err.message);
            }
        });

        return card;
    }

    // ================================================
    // FEED (following + own posts)
    // ================================================

    const feedList = document.getElementById("feedList");
    const feedEmpty = document.getElementById("feedEmpty");

    async function loadFeed() {
        try {
            const data = await skpApiRequest("/posts/feed", { auth: true });
            const posts = data.feed || [];
            feedList.innerHTML = "";
            feedEmpty.style.display = posts.length === 0 ? "block" : "none";
            posts.forEach((p) => feedList.appendChild(renderPostCard(p)));
        } catch (err) {
            showAlert(composerAlert, "error", err.message);
        }
    }

    // ================================================
    // COMPOSER — create post (text / image / video)
    // ================================================

    const composerForm = document.getElementById("composerForm");
    const composerContent = document.getElementById("composerContent");
    const composerImageInput = document.getElementById("composerImageInput");
    const composerVideoInput = document.getElementById("composerVideoInput");
    const composerMediaStatus = document.getElementById("composerMediaStatus");
    const composerVisibility = document.getElementById("composerVisibility");
    const composerAlert = document.getElementById("composerAlert");

    // Only one media type at a time — picking one clears the other.
    composerImageInput.addEventListener("change", () => {
        if (composerImageInput.files[0]) {
            composerVideoInput.value = "";
            composerMediaStatus.textContent = "Selected image: " + composerImageInput.files[0].name;
        }
    });
    composerVideoInput.addEventListener("change", () => {
        if (composerVideoInput.files[0]) {
            composerImageInput.value = "";
            composerMediaStatus.textContent = "Selected video: " + composerVideoInput.files[0].name;
        }
    });

    composerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearAlert(composerAlert);

        const content = composerContent.value.trim();
        const imageFile = composerImageInput.files[0];
        const videoFile = composerVideoInput.files[0];
        const visibility = composerVisibility.value;

        if (!content && !imageFile && !videoFile) {
            showAlert(composerAlert, "error", "Write something or attach a photo/video first.");
            return;
        }

        const btn = composerForm.querySelector("button[type=submit]");
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = "<span>Posting...</span>";

        try {
            let postType = "text";
            let mediaUrl = null;

            if (imageFile) {
                postType = "image";
                const form = new FormData();
                form.append("file", imageFile);
                const uploadRes = await skpApiRequest("/user/upload/post_image", { method: "POST", auth: true, isForm: true, body: form });
                mediaUrl = uploadRes.image;
            } else if (videoFile) {
                postType = "video";
                const form = new FormData();
                form.append("file", videoFile);
                const uploadRes = await skpApiRequest("/user/upload/post_video", { method: "POST", auth: true, isForm: true, body: form });
                mediaUrl = uploadRes.image;
            }

            await skpApiRequest("/posts", {
                method: "POST", auth: true,
                body: { post_type: postType, content, media_url: mediaUrl, visibility },
            });

            composerForm.reset();
            composerMediaStatus.textContent = "";
            showAlert(composerAlert, "success", "Posted!");
            loadFeed();
        } catch (err) {
            showAlert(composerAlert, "error", err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = original;
        }
    });

    // ================================================
    // EXPLORE — public posts only
    // ================================================

    const exploreList = document.getElementById("exploreList");
    const exploreEmpty = document.getElementById("exploreEmpty");
    let exploreLoaded = false;

    async function loadExplore() {
        if (exploreLoaded) return;
        try {
            const data = await skpApiRequest("/posts/explore", { auth: true });
            const posts = data.posts || [];
            exploreList.innerHTML = "";
            exploreEmpty.style.display = posts.length === 0 ? "block" : "none";
            posts.forEach((p) => exploreList.appendChild(renderPostCard(p)));
            exploreLoaded = true;
        } catch (err) {
            exploreEmpty.textContent = err.message;
            exploreEmpty.style.display = "block";
        }
    }

    // ================================================
    // FIND PEOPLE — search + follow/connect actions
    // ================================================

    const searchForm = document.getElementById("searchForm");
    const searchInput = document.getElementById("searchInput");
    const searchResults = document.getElementById("searchResults");

    function renderPersonCard(person) {
        const card = document.createElement("div");
        card.className = "person-card";
        const initials = getInitials(person.name);
        const avatar = person.profile_photo
            ? `<img src="${escapeHtml(fileUrl(person.profile_photo))}" alt="" style="width:40px;height:40px;border-radius:50%;object-fit:cover;">`
            : `<div class="post-card-avatar" style="width:40px;height:40px;">${initials}</div>`;
        const profileLink = person.username ? `profile.html?u=${encodeURIComponent(person.username)}` : "#";

        card.innerHTML = `
            <div class="person-card-info">
                ${avatar}
                <div>
                    <a href="${profileLink}">${escapeHtml(person.name)}</a>
                    <div class="account-meta" style="text-align:left;margin:0;">@${escapeHtml(person.username || "")}</div>
                </div>
            </div>
            <div class="person-card-actions">
                <button type="button" class="follow-btn ${person.is_following ? "" : "primary"}">${person.is_following ? "Following" : "Follow"}</button>
                <button type="button" class="connect-btn" ${person.is_connected ? "disabled" : ""}>${person.is_connected ? "Connected" : "Connect"}</button>
            </div>
        `;

        card.querySelector(".follow-btn").addEventListener("click", async (e) => {
            const btn = e.currentTarget;
            const following = btn.textContent.trim() === "Following";
            try {
                await skpApiRequest(`/social/follow/${person.id}`, { method: following ? "DELETE" : "POST", auth: true });
                btn.textContent = following ? "Follow" : "Following";
                btn.classList.toggle("primary", following);
            } catch (err) {
                alert(err.message);
            }
        });

        card.querySelector(".connect-btn").addEventListener("click", async (e) => {
            const btn = e.currentTarget;
            try {
                await skpApiRequest(`/social/connections/request/${person.id}`, { method: "POST", auth: true, body: {} });
                btn.textContent = "Requested";
                btn.disabled = true;
            } catch (err) {
                alert(err.message);
            }
        });

        return card;
    }

    searchForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const q = searchInput.value.trim();
        if (q.length < 2) return;
        try {
            const data = await skpApiRequest(`/social/search?q=${encodeURIComponent(q)}`, { auth: true });
            searchResults.innerHTML = "";
            (data.results || []).forEach((p) => searchResults.appendChild(renderPersonCard(p)));
            if ((data.results || []).length === 0) {
                searchResults.innerHTML = `<p class="message-empty">No one found matching "${escapeHtml(q)}".</p>`;
            }
        } catch (err) {
            searchResults.innerHTML = `<p class="message-empty">${escapeHtml(err.message)}</p>`;
        }
    });

    // ================================================
    // CONNECTION REQUESTS
    // ================================================

    const requestsList = document.getElementById("requestsList");
    const requestsEmpty = document.getElementById("requestsEmpty");

    async function loadRequests() {
        try {
            const data = await skpApiRequest("/social/connections/pending", { auth: true });
            const pending = data.pending || [];
            requestsList.innerHTML = "";
            requestsEmpty.style.display = pending.length === 0 ? "block" : "none";

            pending.forEach((r) => {
                const card = document.createElement("div");
                card.className = "person-card";
                const requester = r.requester;
                card.innerHTML = `
                    <div class="person-card-info">
                        <div class="post-card-avatar" style="width:40px;height:40px;">${getInitials(requester.name)}</div>
                        <div>
                            <span style="color:#fff;font-weight:600;">${escapeHtml(requester.name)}</span>
                            <div class="account-meta" style="text-align:left;margin:0;">@${escapeHtml(requester.username || "")}</div>
                        </div>
                    </div>
                    <div class="person-card-actions">
                        <button type="button" class="accept-btn primary">Accept</button>
                        <button type="button" class="reject-btn">Reject</button>
                    </div>
                `;
                card.querySelector(".accept-btn").addEventListener("click", async () => {
                    try {
                        await skpApiRequest(`/social/connections/${r.request_id}/accept`, { method: "POST", auth: true });
                        card.remove();
                    } catch (err) { alert(err.message); }
                });
                card.querySelector(".reject-btn").addEventListener("click", async () => {
                    try {
                        await skpApiRequest(`/social/connections/${r.request_id}/reject`, { method: "POST", auth: true });
                        card.remove();
                    } catch (err) { alert(err.message); }
                });
                requestsList.appendChild(card);
            });
        } catch (err) {
            requestsEmpty.textContent = err.message;
            requestsEmpty.style.display = "block";
        }
    }

    // ================================================
    // BOOKMARKS
    // ================================================

    const bookmarksList = document.getElementById("bookmarksList");
    const bookmarksEmpty = document.getElementById("bookmarksEmpty");

    async function loadBookmarks() {
        try {
            const data = await skpApiRequest("/posts/bookmarks", { auth: true });
            const posts = data.bookmarks || [];
            bookmarksList.innerHTML = "";
            bookmarksEmpty.style.display = posts.length === 0 ? "block" : "none";
            posts.forEach((p) => bookmarksList.appendChild(renderPostCard(p)));
        } catch (err) {
            bookmarksEmpty.textContent = err.message;
            bookmarksEmpty.style.display = "block";
        }
    }

    boot();
});
