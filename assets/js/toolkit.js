/* =====================================================
   CYBERSECURITY TOOLKIT — assets/js/toolkit.js
   Tool 1: Password Generator
   (Runs 100% client-side. Nothing here is sent to any server.)
===================================================== */

(function () {

    const CHARSETS = {
        upper: "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        lower: "abcdefghijklmnopqrstuvwxyz",
        numbers: "0123456789",
        symbols: "!@#$%^&*()_+-=[]{}|;:,.<>?",
    };

    const lengthInput = document.getElementById("pwgLength");
    const lengthValue = document.getElementById("pwgLengthValue");
    const upperBox = document.getElementById("pwgUpper");
    const lowerBox = document.getElementById("pwgLower");
    const numbersBox = document.getElementById("pwgNumbers");
    const symbolsBox = document.getElementById("pwgSymbols");
    const output = document.getElementById("pwgOutput");
    const generateBtn = document.getElementById("pwgGenerateBtn");
    const copyBtn = document.getElementById("pwgCopyBtn");
    const strengthFill = document.getElementById("pwgStrengthFill");
    const strengthLabel = document.getElementById("pwgStrengthLabel");

    // Not on the toolkit page (e.g. other pages that don't load this
    // section) — bail out quietly instead of throwing on null elements.
    if (!generateBtn) return;

    // Rejection sampling: avoids the small "modulo bias" you'd get from
    // (randomInt % poolSize). Cryptographically secure randomness comes
    // from window.crypto.getRandomValues, not Math.random().
    function secureRandomIndex(poolSize) {
        const maxValid = Math.floor(0x100000000 / poolSize) * poolSize;
        const buf = new Uint32Array(1);
        let value;
        do {
            window.crypto.getRandomValues(buf);
            value = buf[0];
        } while (value >= maxValid);
        return value % poolSize;
    }

    function buildPool() {
        let pool = "";
        if (upperBox.checked) pool += CHARSETS.upper;
        if (lowerBox.checked) pool += CHARSETS.lower;
        if (numbersBox.checked) pool += CHARSETS.numbers;
        if (symbolsBox.checked) pool += CHARSETS.symbols;
        return pool;
    }

    function generatePassword() {
        const pool = buildPool();
        const length = parseInt(lengthInput.value, 10);

        if (!pool) {
            output.value = "Select at least one character type";
            updateStrength(0, 0);
            return;
        }

        let password = "";
        for (let i = 0; i < length; i++) {
            password += pool[secureRandomIndex(pool.length)];
        }

        output.value = password;
        updateStrength(length, pool.length);
    }

    function updateStrength(length, poolSize) {
        if (!poolSize) {
            strengthFill.style.width = "0%";
            strengthFill.style.background = "transparent";
            strengthLabel.textContent = "—";
            return;
        }

        // Entropy in bits = length * log2(pool size)
        const entropy = length * Math.log2(poolSize);

        let percent, label, color;
        if (entropy < 40) {
            percent = 25; label = "Weak"; color = "#ef4444";
        } else if (entropy < 60) {
            percent = 50; label = "Fair"; color = "#f59e0b";
        } else if (entropy < 80) {
            percent = 75; label = "Strong"; color = "#38bdf8";
        } else {
            percent = 100; label = "Very Strong"; color = "#22c55e";
        }

        strengthFill.style.width = percent + "%";
        strengthFill.style.background = color;
        strengthLabel.textContent = label;
    }

    async function copyPassword() {
        if (!output.value || output.value.startsWith("Select") || output.value.startsWith("Click")) {
            return;
        }
        try {
            await navigator.clipboard.writeText(output.value);
        } catch (err) {
            // Fallback for browsers/contexts without Clipboard API access
            output.select();
            document.execCommand("copy");
        }
        const icon = copyBtn.querySelector("i");
        icon.classList.remove("fa-copy");
        icon.classList.add("fa-check");
        copyBtn.classList.add("copied");
        setTimeout(() => {
            icon.classList.remove("fa-check");
            icon.classList.add("fa-copy");
            copyBtn.classList.remove("copied");
        }, 1500);
    }

    lengthInput.addEventListener("input", () => {
        lengthValue.textContent = lengthInput.value;
    });

    generateBtn.addEventListener("click", generatePassword);
    copyBtn.addEventListener("click", copyPassword);

    // Give a first password immediately so the tool doesn't look empty.
    generatePassword();

})();


/* =====================================================
   Tool 2: Hash Generator
   Uses the browser's native Web Crypto API (SubtleCrypto).
   Nothing typed here is sent to any server.
===================================================== */
(function () {

    const input = document.getElementById("hgInput");
    const algoSelect = document.getElementById("hgAlgo");
    const output = document.getElementById("hgOutput");
    const generateBtn = document.getElementById("hgGenerateBtn");
    const copyBtn = document.getElementById("hgCopyBtn");

    // Card not present on this page — bail out quietly.
    if (!generateBtn) return;

    async function generateHash() {
        const text = input.value;

        if (!text) {
            output.value = "Type some text first";
            return;
        }

        // SubtleCrypto requires a secure context (HTTPS or localhost).
        if (!window.crypto || !window.crypto.subtle) {
            output.value = "Web Crypto API unavailable (requires HTTPS)";
            return;
        }

        const encoded = new TextEncoder().encode(text);
        const algo = algoSelect.value;
        const digestBuffer = await window.crypto.subtle.digest(algo, encoded);

        // Convert ArrayBuffer -> hex string
        const hex = Array.from(new Uint8Array(digestBuffer))
            .map((b) => b.toString(16).padStart(2, "0"))
            .join("");

        output.value = hex;
    }

    async function copyHash() {
        if (!output.value || output.value.startsWith("Type") || output.value.startsWith("Hash will") || output.value.startsWith("Web Crypto")) {
            return;
        }
        try {
            await navigator.clipboard.writeText(output.value);
        } catch (err) {
            output.select();
            document.execCommand("copy");
        }
        const icon = copyBtn.querySelector("i");
        icon.classList.remove("fa-copy");
        icon.classList.add("fa-check");
        copyBtn.classList.add("copied");
        setTimeout(() => {
            icon.classList.remove("fa-check");
            icon.classList.add("fa-copy");
            copyBtn.classList.remove("copied");
        }, 1500);
    }

    generateBtn.addEventListener("click", generateHash);
    copyBtn.addEventListener("click", copyHash);
    algoSelect.addEventListener("change", () => {
        if (input.value) generateHash();
    });

})();


/* =====================================================
   Tool 3: Password Strength Checker
   Checks a typed password against basic composition rules,
   a small common-password list, and an entropy estimate.
   Nothing typed here is sent anywhere or stored.
===================================================== */
(function () {

    const input = document.getElementById("pscInput");
    const toggleBtn = document.getElementById("pscToggleBtn");
    const strengthFill = document.getElementById("pscStrengthFill");
    const strengthLabel = document.getElementById("pscStrengthLabel");
    const crackTimeEl = document.getElementById("pscCrackTime");

    const ruleLength = document.getElementById("pscRuleLength");
    const ruleUpperLower = document.getElementById("pscRuleUpperLower");
    const ruleNumber = document.getElementById("pscRuleNumber");
    const ruleSymbol = document.getElementById("pscRuleSymbol");
    const ruleCommon = document.getElementById("pscRuleCommon");

    // Card not present on this page — bail out quietly.
    if (!input) return;

    // Small sample of the most commonly leaked passwords (not exhaustive —
    // this is a quick sanity check, not a full breach-database lookup).
    const COMMON_PASSWORDS = new Set([
        "123456", "123456789", "password", "qwerty", "12345678", "111111",
        "123123", "abc123", "password1", "iloveyou", "admin", "welcome",
        "monkey", "letmein", "dragon", "football", "1234567", "12345",
        "qwerty123", "000000", "1q2w3e4r", "sunshine", "princess",
        "trustno1", "master", "password123", "superman", "michael",
    ]);

    function setRule(el, isValid) {
        el.classList.toggle("valid", isValid);
        const icon = el.querySelector("i");
        icon.classList.toggle("fa-circle-xmark", !isValid);
        icon.classList.toggle("fa-circle-check", isValid);
    }

    function formatCrackTime(seconds) {
        if (!isFinite(seconds) || seconds < 1) return "instantly";
        const units = [
            ["years", 31536000], ["days", 86400],
            ["hours", 3600], ["minutes", 60], ["seconds", 1],
        ];
        for (const [name, size] of units) {
            if (seconds >= size) {
                const value = seconds / size;
                if (name === "years" && value > 1e6) return "millions of years";
                return `${value.toFixed(value < 10 ? 1 : 0)} ${name}`;
            }
        }
        return "instantly";
    }

    function checkPassword() {
        const pw = input.value;

        const hasLower = /[a-z]/.test(pw);
        const hasUpper = /[A-Z]/.test(pw);
        const hasNumber = /[0-9]/.test(pw);
        const hasSymbol = /[^a-zA-Z0-9]/.test(pw);
        const isLongEnough = pw.length >= 12;
        const isCommon = COMMON_PASSWORDS.has(pw.toLowerCase());

        setRule(ruleLength, isLongEnough);
        setRule(ruleUpperLower, hasLower && hasUpper);
        setRule(ruleNumber, hasNumber);
        setRule(ruleSymbol, hasSymbol);
        setRule(ruleCommon, pw.length > 0 && !isCommon);

        if (!pw) {
            strengthFill.style.width = "0%";
            strengthFill.style.background = "transparent";
            strengthLabel.textContent = "—";
            crackTimeEl.textContent = "Estimated time to crack: —";
            return;
        }

        if (isCommon) {
            strengthFill.style.width = "10%";
            strengthFill.style.background = "#ef4444";
            strengthLabel.textContent = "Very Weak";
            crackTimeEl.textContent = "Estimated time to crack: instantly (known leaked password)";
            return;
        }

        // Rough entropy estimate: figure out which character classes are
        // present, sum their pool sizes, entropy = length * log2(poolSize).
        // Same approach as the Password Generator tool above, applied to
        // whatever the user actually typed instead of a chosen charset.
        let poolSize = 0;
        if (hasLower) poolSize += 26;
        if (hasUpper) poolSize += 26;
        if (hasNumber) poolSize += 10;
        if (hasSymbol) poolSize += 32;

        const entropy = pw.length * Math.log2(poolSize || 1);

        let percent, label, color;
        if (entropy < 40) {
            percent = 25; label = "Weak"; color = "#ef4444";
        } else if (entropy < 60) {
            percent = 50; label = "Fair"; color = "#f59e0b";
        } else if (entropy < 80) {
            percent = 75; label = "Strong"; color = "#38bdf8";
        } else {
            percent = 100; label = "Very Strong"; color = "#22c55e";
        }

        strengthFill.style.width = percent + "%";
        strengthFill.style.background = color;
        strengthLabel.textContent = label;

        // Assume a fast offline attack: 10 billion guesses/sec (roughly
        // what a modern GPU rig can do against an unsalted fast hash —
        // deliberately a conservative/pessimistic assumption).
        const guesses = Math.pow(2, entropy);
        const seconds = guesses / 10e9;
        crackTimeEl.textContent = `Estimated time to crack: ${formatCrackTime(seconds)} (worst-case offline attack estimate)`;
    }

    function togglePasswordVisibility() {
        const isPassword = input.type === "password";
        input.type = isPassword ? "text" : "password";
        const icon = toggleBtn.querySelector("i");
        icon.classList.toggle("fa-eye", !isPassword);
        icon.classList.toggle("fa-eye-slash", isPassword);
    }

    input.addEventListener("input", checkPassword);
    toggleBtn.addEventListener("click", togglePasswordVisibility);

})();
