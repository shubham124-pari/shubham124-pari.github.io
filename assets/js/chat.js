// =====================================================
// chat.html logic — Private Chat (Socket.IO real-time client)
// Relies on globals from auth.js: skpApiRequest, skpGetSessionUser,
// skpVerifySession, SKP_API_BASE, SKP_TOKEN_KEY.
// Relies on CDN globals: io (socket.io-client), marked, hljs.
// =====================================================

document.addEventListener("DOMContentLoaded", async () => {

    const guard = document.getElementById("dashboardGuard");
    const app = document.getElementById("chatApp");
    const dashSignInBtn = document.getElementById("dashboardSignInBtn");

    // Only run this file's logic on chat.html (it's a shared bundle-free
    // site, but chat.html-only elements guard that automatically).
    if (!app) return;

    if (dashSignInBtn) {
        dashSignInBtn.addEventListener("click", () => {
            const btn = document.getElementById("signInBtn");
            if (btn) btn.click();
        });
    }

    const conversationList = document.getElementById("conversationList");
    const conversationsEmpty = document.getElementById("conversationsEmpty");
    const chatMainEmpty = document.getElementById("chatMainEmpty");
    const chatThread = document.getElementById("chatThread");
    const threadAvatar = document.getElementById("threadAvatar");
    const threadName = document.getElementById("threadName");
    const threadStatus = document.getElementById("threadStatus");
    const threadMessages = document.getElementById("threadMessages");
    const loadMoreBtn = document.getElementById("loadMoreBtn");
    const threadTypingRow = document.getElementById("threadTypingRow");
    const composeForm = document.getElementById("composeForm");
    const composeInput = document.getElementById("composeInput");
    const attachImageInput = document.getElementById("attachImageInput");
    const attachDocInput = document.getElementById("attachDocInput");
    const chatAlert = document.getElementById("chatAlert");
    const chatSearchInput = document.getElementById("chatSearchInput");
    const chatSearchResults = document.getElementById("chatSearchResults");
    const newChatBtn = document.getElementById("newChatBtn");
    const chatPickerOverlay = document.getElementById("chatPickerOverlay");
    const chatPickerClose = document.getElementById("chatPickerClose");
    const chatPickerSearch = document.getElementById("chatPickerSearch");
    const chatPickerList = document.getElementById("chatPickerList");

    let currentUser = null;
    let socket = null;
    let conversations = [];      // cached sidebar list
    let activeConversationId = null;
    let activeOtherUser = null;
    let oldestLoadedMessageId = null;
    let typingTimeout = null;
    let lastSeenMessageId = null;

    // ---------------- small helpers ----------------

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str == null ? "" : String(str);
        return div.innerHTML;
    }

    function fileUrl(relativePath) {
        if (!relativePath) return null;
        const origin = SKP_API_BASE.replace(/\/api\/?$/, "");
        return origin + relativePath;
    }

    function backendOrigin() {
        return SKP_API_BASE.replace(/\/api\/?$/, "");
    }

    function getInitials(name) {
        return (name || "?").trim().split(/\s+/).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
    }

    function timeAgo(iso) {
        if (!iso) return "";
        const diff = (Date.now() - new Date(iso).getTime()) / 1000;
        if (diff < 60) return "just now";
        if (diff < 3600) return Math.floor(diff / 60) + "m ago";
        if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
        return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
    }

    function formatClock(iso) {
        if (!iso) return "";
        return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
    }

    // Renders message text as Markdown with highlighted code blocks.
    // marked + hljs are loaded via CDN in chat.html; if either failed to
    // load (offline CDN, ad-blocker) we fall back to escaped plain text
    // instead of breaking the page.
    function renderMarkdown(text) {
        if (typeof marked === "undefined") return escapeHtml(text);
        try {
            const html = marked.parse(text, { breaks: true });
            const wrapper = document.createElement("div");
            wrapper.innerHTML = html;
            if (typeof hljs !== "undefined") {
                wrapper.querySelectorAll("pre code").forEach((block) => hljs.highlightElement(block));
            }
            wrapper.querySelectorAll("a").forEach((a) => {
                a.setAttribute("target", "_blank");
                a.setAttribute("rel", "noopener noreferrer");
            });
            return wrapper.innerHTML;
        } catch (e) {
            return escapeHtml(text);
        }
    }

    function showAlert(text, type) {
        if (!chatAlert) return;
        chatAlert.textContent = text;
        chatAlert.className = "chat-alert show " + (type || "error");
        setTimeout(() => { chatAlert.className = "chat-alert"; }, 4000);
    }

    // ---------------- boot / auth guard ----------------

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
        app.style.display = "grid";
        connectSocket();
        await loadConversations();
    }

    // ---------------- Socket.IO ----------------

    function connectSocket() {
        if (typeof io === "undefined") {
            showAlert("Real-time connection library failed to load. Refresh the page.", "error");
            return;
        }
        const token = localStorage.getItem(SKP_TOKEN_KEY);
        socket = io(backendOrigin(), { auth: { token }, transports: ["websocket", "polling"] });

        socket.on("connect_error", () => {
            showAlert("Couldn't connect to chat. Retrying...", "error");
        });

        socket.on("presence", ({ user }) => {
            const conv = conversations.find((c) => c.other_user.id === user.id);
            if (conv) conv.other_user = user;
            renderConversationList();
            if (activeOtherUser && activeOtherUser.id === user.id) {
                activeOtherUser = user;
                renderThreadHeader();
            }
        });

        socket.on("new_message", (message) => {
            if (message.conversation_id === activeConversationId) {
                appendMessage(message, true);
                markReadIfNeeded(message);
            }
            upsertConversationPreview(message.conversation_id, message);
        });

        socket.on("conversation_update", ({ conversation_id, last_message }) => {
            if (conversation_id !== activeConversationId) {
                upsertConversationPreview(conversation_id, last_message, true);
            }
        });

        socket.on("typing", ({ conversation_id, is_typing }) => {
            if (conversation_id !== activeConversationId) return;
            threadTypingRow.style.display = is_typing ? "flex" : "none";
        });

        socket.on("read_receipt", ({ conversation_id, message_id }) => {
            if (conversation_id !== activeConversationId) return;
            document.querySelectorAll(`.chat-bubble-row[data-mine="true"]`).forEach((row) => {
                const id = parseInt(row.dataset.id, 10);
                const tick = row.querySelector(".chat-tick");
                if (tick && id <= message_id) tick.classList.add("read");
            });
        });

        socket.on("message_deleted", ({ conversation_id, message_id }) => {
            if (conversation_id !== activeConversationId) return;
            const row = threadMessages.querySelector(`[data-id="${message_id}"]`);
            if (row) {
                row.querySelector(".chat-bubble-body").innerHTML =
                    '<em class="chat-deleted">This message was deleted</em>';
                row.querySelector(".chat-msg-actions")?.remove();
            }
        });

        socket.on("error", (err) => showAlert(err.error || "Something went wrong.", "error"));
    }

    // ---------------- conversation list (sidebar) ----------------

    async function loadConversations() {
        try {
            const data = await skpApiRequest("/chat/conversations", { auth: true });
            conversations = data.conversations;
            renderConversationList();
        } catch (err) {
            showAlert(err.message, "error");
        }
    }

    function upsertConversationPreview(conversationId, message, bumpUnread) {
        let conv = conversations.find((c) => c.conversation_id === conversationId);
        if (!conv) {
            loadConversations();
            return;
        }
        conv.last_message = message;
        if (bumpUnread) conv.unread_count = (conv.unread_count || 0) + 1;
        conversations = conversations.filter((c) => c.conversation_id !== conversationId);
        conversations.unshift(conv);
        renderConversationList();
    }

    function renderConversationList() {
        conversationList.innerHTML = "";
        conversationsEmpty.style.display = conversations.length ? "none" : "block";

        conversations.forEach((conv) => {
            const other = conv.other_user;
            const last = conv.last_message;
            let preview = "No messages yet";
            if (last) {
                if (last.deleted) preview = "Message deleted";
                else if (last.message_type === "image") preview = "📷 Photo";
                else if (last.message_type === "document") preview = "📎 " + (last.attachment_name || "Document");
                else preview = (last.body || "").slice(0, 60);
            }

            const li = document.createElement("li");
            li.className = "chat-conv-item" + (conv.conversation_id === activeConversationId ? " active" : "");
            li.innerHTML = `
                <div class="chat-avatar-wrap">
                    <img src="${other.profile_photo ? fileUrl(other.profile_photo) : "assets/images/profile.png"}" class="chat-avatar" alt="">
                    <span class="chat-online-dot ${other.is_online ? "online" : ""}"></span>
                </div>
                <div class="chat-conv-info">
                    <h5>${escapeHtml(other.name)}</h5>
                    <p>${escapeHtml(preview)}</p>
                </div>
                <div class="chat-conv-meta">
                    <span class="chat-conv-time">${last ? timeAgo(last.created_at) : ""}</span>
                    ${conv.unread_count ? `<span class="chat-unread-badge">${conv.unread_count}</span>` : ""}
                </div>
            `;
            li.addEventListener("click", () => openConversation(conv.conversation_id, other));
            conversationList.appendChild(li);
        });
    }

    // ---------------- thread (open conversation) ----------------

    async function openConversation(conversationId, otherUser) {
        if (activeConversationId) socket.emit("leave_conversation", { conversation_id: activeConversationId });

        activeConversationId = conversationId;
        activeOtherUser = otherUser;
        oldestLoadedMessageId = null;
        lastSeenMessageId = null;

        chatMainEmpty.style.display = "none";
        chatThread.style.display = "flex";
        threadMessages.innerHTML = "";
        threadMessages.appendChild(loadMoreBtn);
        loadMoreBtn.style.display = "none";
        threadTypingRow.style.display = "none";

        renderThreadHeader();
        socket.emit("join_conversation", { conversation_id: conversationId });

        const conv = conversations.find((c) => c.conversation_id === conversationId);
        if (conv) conv.unread_count = 0;
        renderConversationList();

        await loadMessages();
    }

    function renderThreadHeader() {
        threadAvatar.src = activeOtherUser.profile_photo ? fileUrl(activeOtherUser.profile_photo) : "assets/images/profile.png";
        threadName.textContent = activeOtherUser.name;
        threadStatus.textContent = activeOtherUser.is_online
            ? "Online"
            : (activeOtherUser.last_seen ? "Last seen " + timeAgo(activeOtherUser.last_seen) : "Offline");
    }

    async function loadMessages() {
        try {
            const params = oldestLoadedMessageId ? `?before=${oldestLoadedMessageId}&limit=30` : "?limit=30";
            const data = await skpApiRequest(`/chat/conversations/${activeConversationId}/messages${params}`, { auth: true });

            const scrollAnchor = threadMessages.scrollHeight - threadMessages.scrollTop;
            data.messages.forEach((m) => appendMessage(m, false, true));
            if (!oldestLoadedMessageId) threadMessages.scrollTop = threadMessages.scrollHeight;
            else threadMessages.scrollTop = threadMessages.scrollHeight - scrollAnchor;

            if (data.messages.length) oldestLoadedMessageId = data.messages[0].id;
            loadMoreBtn.style.display = data.has_more ? "block" : "none";

            const last = data.messages[data.messages.length - 1];
            if (last) markReadIfNeeded(last);
        } catch (err) {
            showAlert(err.message, "error");
        }
    }

    loadMoreBtn.addEventListener("click", loadMessages);

    function markReadIfNeeded(message) {
        if (!message || message.sender_id === currentUser.id) return;
        if (lastSeenMessageId && message.id <= lastSeenMessageId) return;
        lastSeenMessageId = message.id;
        socket.emit("mark_read", { conversation_id: activeConversationId, message_id: message.id });
    }

    function appendMessage(message, animate, prepend) {
        const mine = message.sender_id === currentUser.id;
        const row = document.createElement("div");
        row.className = "chat-bubble-row" + (mine ? " mine" : "");
        row.dataset.id = message.id;
        row.dataset.mine = mine ? "true" : "false";

        let bodyHtml;
        if (message.deleted) {
            bodyHtml = '<em class="chat-deleted">This message was deleted</em>';
        } else if (message.message_type === "image") {
            bodyHtml = `<a href="${fileUrl(message.attachment_url)}" target="_blank" rel="noopener"><img class="chat-img-attachment" src="${fileUrl(message.attachment_url)}" alt="shared image"></a>`;
            if (message.body) bodyHtml += `<div class="chat-markdown">${renderMarkdown(message.body)}</div>`;
        } else if (message.message_type === "document") {
            bodyHtml = `<a class="chat-doc-attachment" href="${fileUrl(message.attachment_url)}" target="_blank" rel="noopener">
                <i class="fa-solid fa-file"></i> ${escapeHtml(message.attachment_name || "Document")}
            </a>`;
        } else {
            bodyHtml = `<div class="chat-markdown">${renderMarkdown(message.body || "")}</div>`;
        }

        row.innerHTML = `
            <div class="chat-bubble-body">${bodyHtml}</div>
            <div class="chat-bubble-meta">
                <span>${formatClock(message.created_at)}</span>
                ${mine ? '<i class="fa-solid fa-check chat-tick"></i>' : ""}
            </div>
            ${mine && !message.deleted ? '<div class="chat-msg-actions"><button type="button" class="chat-delete-btn" title="Delete"><i class="fa-solid fa-trash"></i></button></div>' : ""}
        `;

        const deleteBtn = row.querySelector(".chat-delete-btn");
        if (deleteBtn) {
            deleteBtn.addEventListener("click", () => {
                if (!confirm("Delete this message?")) return;
                socket.emit("delete_message", { message_id: message.id });
                skpApiRequest(`/chat/messages/${message.id}`, { method: "DELETE", auth: true }).catch(() => {});
            });
        }

        if (prepend) threadMessages.insertBefore(row, loadMoreBtn.nextSibling);
        else threadMessages.appendChild(row);

        if (animate) threadMessages.scrollTop = threadMessages.scrollHeight;
    }

    // ---------------- compose / send ----------------

    composeForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const body = composeInput.value.trim();
        if (!body || !activeConversationId) return;
        socket.emit("send_message", { conversation_id: activeConversationId, message_type: "text", body });
        composeInput.value = "";
        stopTyping();
    });

    let isTyping = false;
    function startTyping() {
        if (!activeConversationId) return;
        if (!isTyping) {
            isTyping = true;
            socket.emit("typing", { conversation_id: activeConversationId, is_typing: true });
        }
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(stopTyping, 2000);
    }
    function stopTyping() {
        if (isTyping && activeConversationId) {
            isTyping = false;
            socket.emit("typing", { conversation_id: activeConversationId, is_typing: false });
        }
    }
    composeInput.addEventListener("input", startTyping);
    composeInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            composeForm.requestSubmit();
        }
    });

    async function sendAttachment(file, kind) {
        if (!file || !activeConversationId) return;
        const form = new FormData();
        form.append("file", file);
        try {
            const data = await skpApiRequest(`/user/upload/${kind}`, { method: "POST", body: form, auth: true, isForm: true });
            socket.emit("send_message", {
                conversation_id: activeConversationId,
                message_type: kind === "chat_image" ? "image" : "document",
                attachment_url: data.url,
                attachment_name: data.original_name,
            });
        } catch (err) {
            showAlert(err.message, "error");
        }
    }
    attachImageInput.addEventListener("change", () => {
        sendAttachment(attachImageInput.files[0], "chat_image");
        attachImageInput.value = "";
    });
    attachDocInput.addEventListener("change", () => {
        sendAttachment(attachDocInput.files[0], "chat_document");
        attachDocInput.value = "";
    });

    // ---------------- search ----------------

    let searchDebounce = null;
    chatSearchInput.addEventListener("input", () => {
        clearTimeout(searchDebounce);
        const q = chatSearchInput.value.trim();
        if (q.length < 2) {
            chatSearchResults.innerHTML = "";
            chatSearchResults.style.display = "none";
            return;
        }
        searchDebounce = setTimeout(async () => {
            try {
                const data = await skpApiRequest(`/chat/search?q=${encodeURIComponent(q)}`, { auth: true });
                renderSearchResults(data.results);
            } catch (err) {
                // silent — search box isn't a great place for a full alert
            }
        }, 300);
    });

    function renderSearchResults(results) {
        chatSearchResults.style.display = "block";
        if (!results.length) {
            chatSearchResults.innerHTML = '<p class="message-empty">No messages found.</p>';
            return;
        }
        chatSearchResults.innerHTML = "";
        results.forEach((m) => {
            const conv = conversations.find((c) => c.conversation_id === m.conversation_id);
            const div = document.createElement("div");
            div.className = "chat-search-result";
            div.innerHTML = `<strong>${conv ? escapeHtml(conv.other_user.name) : "Conversation"}</strong><p>${escapeHtml((m.body || "").slice(0, 80))}</p>`;
            div.addEventListener("click", () => {
                if (conv) openConversation(conv.conversation_id, conv.other_user);
                chatSearchResults.style.display = "none";
                chatSearchInput.value = "";
            });
            chatSearchResults.appendChild(div);
        });
    }

    // ---------------- new chat picker ----------------

    newChatBtn.addEventListener("click", async () => {
        chatPickerOverlay.classList.add("open");
        chatPickerSearch.value = "";
        await loadPickerUsers("");
    });
    chatPickerClose.addEventListener("click", () => chatPickerOverlay.classList.remove("open"));

    let pickerDebounce = null;
    chatPickerSearch.addEventListener("input", () => {
        clearTimeout(pickerDebounce);
        pickerDebounce = setTimeout(() => loadPickerUsers(chatPickerSearch.value.trim()), 250);
    });

    async function loadPickerUsers(search) {
        try {
            const data = await skpApiRequest(`/chat/users?search=${encodeURIComponent(search)}`, { auth: true });
            chatPickerList.innerHTML = "";
            data.users.forEach((u) => {
                const li = document.createElement("li");
                li.innerHTML = `
                    <img src="${u.profile_photo ? fileUrl(u.profile_photo) : "assets/images/profile.png"}" class="chat-avatar" alt="">
                    <div><h5>${escapeHtml(u.name)}</h5><p>${escapeHtml(u.email)}</p></div>
                `;
                li.addEventListener("click", async () => {
                    const res = await skpApiRequest("/chat/conversations", { method: "POST", auth: true, body: { user_id: u.id } });
                    chatPickerOverlay.classList.remove("open");
                    await loadConversations();
                    openConversation(res.conversation_id, res.other_user);
                });
                chatPickerList.appendChild(li);
            });
        } catch (err) {
            showAlert(err.message, "error");
        }
    }

    boot();
});
