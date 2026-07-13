// =====================================================
// Kali-style Matrix Rain Background
// Subtle, low-opacity animated code rain behind the site
// content — gives the portfolio a hacker / terminal feel.
// Respects prefers-reduced-motion.
// =====================================================

(function () {

    const canvas = document.getElementById("matrixRain");
    if (!canvas) return;

    const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    if (prefersReducedMotion) {
        canvas.style.display = "none";
        return;
    }

    const ctx = canvas.getContext("2d");
    const glyphs = "01アイウエオカキクケコサシスセソ$#@%&<>{}[]/\\|+=*";

    let columns = 0;
    let drops = [];
    const fontSize = 15;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        columns = Math.ceil(canvas.width / fontSize);
        drops = new Array(columns).fill(0).map(() => Math.floor(Math.random() * -50));
    }

    function draw() {
        ctx.fillStyle = "rgba(5, 7, 15, 0.09)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.font = fontSize + "px monospace";

        for (let i = 0; i < columns; i++) {
            const char = glyphs[Math.floor(Math.random() * glyphs.length)];
            const x = i * fontSize;
            const y = drops[i] * fontSize;

            ctx.fillStyle = "rgba(0, 255, 128, 0.55)";
            ctx.fillText(char, x, y);

            if (y > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }
            drops[i]++;
        }
    }

    resize();
    window.addEventListener("resize", resize);

    let rafId = null;
    let last = 0;
    const interval = 60; // ms between frames — keeps it subtle & light on CPU

    function loop(ts) {
        rafId = requestAnimationFrame(loop);
        if (ts - last < interval) return;
        last = ts;
        draw();
    }

    rafId = requestAnimationFrame(loop);

    // Pause when tab is hidden to save battery/CPU
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            cancelAnimationFrame(rafId);
        } else {
            rafId = requestAnimationFrame(loop);
        }
    });

})();
