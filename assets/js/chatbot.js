// =====================================================
// Floating AI chatbot widget — injected on every page.
// Talks to /api/chatbot/ask. Works for signed-out visitors
// too; if the visitor is signed in, their chats are linked
// to their account automatically (backend reads the Bearer
// token if present).
//
// Multilingual: the backend auto-detects the visitor's
// language and replies in the same one — this file just
// renders whatever comes back.
// Markdown + code highlighting: answers are rendered with
// marked.js (Markdown) and highlight.js (fenced code blocks),
// loaded from CDN on demand so pages that never open the
// widget don't pay for it.
// =====================================================

document.addEventListener("DOMContentLoaded", () => {

    // ---------------- load marked.js + highlight.js on demand ----------------

    let assetsReady = null;
    function loadChatRenderAssets() {
        if (assetsReady) return assetsReady;

        const needsHljsCss = !document.querySelector('link[data-chat-hljs-theme]');
        if (needsHljsCss) {
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css";
            link.setAttribute("data-chat-hljs-theme", "1");
            document.head.appendChild(link);
        }

        function loadScript(src) {
            return new Promise((resolve) => {
                const existing = document.querySelector(`script[src="${src}"]`);
                if (existing) { existing.addEventListener("load", resolve); if (existing.dataset.loaded) resolve(); return; }
                const script = document.createElement("script");
                script.src = src;
                script.onload = () => { script.dataset.loaded = "1"; resolve(); };
                script.onerror = resolve; // fall back to plain text rendering
                document.body.appendChild(script);
            });
        }

        assetsReady = Promise.all([
            typeof marked === "undefined"
                ? loadScript("https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js")
                : Promise.resolve(),
            typeof hljs === "undefined"
                ? loadScript("https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js")
                : Promise.resolve(),
        ]);
        return assetsReady;
    }

    // ---------------- inject markup ----------------

    const bubble = document.createElement("button");
    bubble.className = "chat-bubble";
    bubble.id = "chatBubble";
    bubble.type = "button";
    bubble.setAttribute("aria-label", "Open chat assistant");
    bubble.innerHTML = '<i class="fa-solid fa-robot"></i>';

    const win = document.createElement("div");
    win.className = "chat-window";
    win.id = "chatWindow";
    win.innerHTML = `
        <div class="chat-window-header">
            <h4><i class="fa-solid fa-robot"></i> Ask about Shubham</h4>
            <button type="button" class="chat-window-close" id="chatWindowClose" aria-label="Close chat">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="chat-messages" id="chatMessages"></div>
        <form class="chat-input-row" id="chatForm">
            <input type="text" id="chatInput" placeholder="Ask anything — code, cybersecurity, career, resume, or Shubham's work..." maxlength="500" autocomplete="off">
            <button type="submit" id="chatSend" aria-label="Send">
                <i class="fa-solid fa-paper-plane"></i>
            </button>
        </form>
    `;

    document.body.appendChild(bubble);
    document.body.appendChild(win);

    const messagesEl = document.getElementById("chatMessages");
    const form = document.getElementById("chatForm");
    const input = document.getElementById("chatInput");
    const sendBtn = document.getElementById("chatSend");
    const closeBtn = document.getElementById("chatWindowClose");

    // Client-side conversation memory for THIS browser session — sent
    // back to the server on every ask() call so anonymous/signed-out
    // visitors still get follow-up context, not just logged-in users
    // (whose history the server keeps in the database instead).
    const sessionHistory = [];
    const MAX_SESSION_TURNS = 6;

    // ---------------- helpers ----------------

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str == null ? "" : String(str);
        return div.innerHTML;
    }

    function renderBotHtml(text) {
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

    function addMessage(text, kind) {
        const div = document.createElement("div");
        div.className = "chat-msg " + kind;
        if (kind === "bot") {
            div.innerHTML = renderBotHtml(text);
        } else {
            div.textContent = text;
        }
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return div;
    }

    function addTyping() {
        const div = document.createElement("div");
        div.className = "chat-typing";
        div.id = "chatTypingIndicator";
        div.innerHTML = "<span></span><span></span><span></span>";
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return div;
    }

    function removeTyping() {
        const el = document.getElementById("chatTypingIndicator");
        if (el) el.remove();
    }

    let greeted = false;
    function greet() {
        if (greeted) return;
        greeted = true;
        addMessage(
            "Hi! I'm Shubham's multilingual AI assistant \u2014 ask me about programming, " +
            "cybersecurity, careers, resumes, or Shubham's own projects and skills. " +
            "I'll reply in whatever language you write in.",
            "bot"
        );
    }

    // ---------------- open/close ----------------

    bubble.addEventListener("click", () => {
        win.classList.add("open");
        loadChatRenderAssets();
        greet();
        input.focus();
    });

    closeBtn.addEventListener("click", () => win.classList.remove("open"));

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") win.classList.remove("open");
    });

    // ---------------- ask ----------------

    // API base is defined in auth.js (loaded before this file on every
    // page). If auth.js somehow isn't present, fall back to same-origin.
    function apiBase() {
        if (typeof SKP_API_BASE !== "undefined") return SKP_API_BASE;
        return "/api";
    }

    async function askBot(question) {
        const headers = { "Content-Type": "application/json" };
        const token = localStorage.getItem("skp_token");
        if (token) headers.Authorization = "Bearer " + token;

        const res = await fetch(apiBase() + "/chatbot/ask", {
            method: "POST",
            headers,
            body: JSON.stringify({ question, history: sessionHistory }),
        });

        let data = {};
        try { data = await res.json(); } catch (e) { /* empty */ }

        if (!res.ok) {
            throw new Error(data.error || "Something went wrong. Please try again.");
        }
        return data.answer;
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const question = input.value.trim();
        if (!question) return;

        addMessage(question, "user");
        input.value = "";
        input.disabled = true;
        sendBtn.disabled = true;

        const typing = addTyping();

        try {
            await loadChatRenderAssets();
            const answer = await askBot(question);
            removeTyping();
            addMessage(answer, "bot");

            sessionHistory.push({ question, answer });
            if (sessionHistory.length > MAX_SESSION_TURNS) sessionHistory.shift();
        } catch (err) {
            removeTyping();
            addMessage(err.message, "error");
        } finally {
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        }
    });
});
