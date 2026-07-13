// ===============================
// Portfolio JavaScript
// Author : Shubham Kumar
// ===============================

// ===============================
// Page Transition (advanced tech wipe effect)
// ===============================

const pageTransition = document.getElementById("pageTransition");

window.addEventListener("DOMContentLoaded", () => {
    if (pageTransition) {
        requestAnimationFrame(() => {
            pageTransition.classList.add("leave");
        });
    }
});

document.querySelectorAll('a[href$=".html"]').forEach((link) => {
    link.addEventListener("click", (e) => {
        const href = link.getAttribute("href");
        if (!href || href.startsWith("#") || link.hasAttribute("download") || link.target === "_blank") {
            return;
        }
        e.preventDefault();
        if (pageTransition) {
            pageTransition.classList.remove("leave");
            pageTransition.classList.add("enter");
            setTimeout(() => {
                window.location.href = href;
            }, 550);
        } else {
            window.location.href = href;
        }
    });
});


// ===============================
// Sign In Modal
// ===============================

const signInBtn = document.getElementById("signInBtn");
const signInOverlay = document.getElementById("signInOverlay");
const signInClose = document.getElementById("signInClose");
const signInEmailToggle = document.getElementById("signInEmailToggle");
const signInEmailForm = document.getElementById("signInEmailForm");

if (signInBtn && signInOverlay) {

    signInBtn.addEventListener("click", () => {
        signInOverlay.classList.add("active");
    });

    signInClose.addEventListener("click", () => {
        signInOverlay.classList.remove("active");
    });

    signInOverlay.addEventListener("click", (e) => {
        if (e.target === signInOverlay) {
            signInOverlay.classList.remove("active");
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            signInOverlay.classList.remove("active");
        }
    });

    if (signInEmailToggle && signInEmailForm) {
        signInEmailToggle.addEventListener("click", () => {
            signInEmailForm.classList.toggle("active");
        });

        signInEmailForm.addEventListener("submit", (e) => {
            e.preventDefault();
            signInEmailForm.querySelector(".signin-submit").textContent = "Check your inbox ✔";
        });
    }

    document.querySelectorAll(".signin-option.google, .signin-option.facebook").forEach((btn) => {
        btn.addEventListener("click", () => {
            const original = btn.innerHTML;
            btn.innerHTML = "Coming soon...";
            setTimeout(() => { btn.innerHTML = original; }, 1500);
        });
    });
}


// ===============================
// Mobile Menu Toggle
// ===============================

const menuToggle = document.getElementById("menuToggle");
const navMenu = document.getElementById("navMenu");

if (menuToggle && navMenu) {

    menuToggle.addEventListener("click", () => {
        navMenu.classList.toggle("active");

        const icon = menuToggle.querySelector("i");
        if (icon) {
            icon.classList.toggle("fa-bars");
            icon.classList.toggle("fa-xmark");
        }
    });

    // Close menu when a link is clicked
    document.querySelectorAll(".nav-menu .nav-link, .nav-menu .resume-button").forEach((link) => {
        link.addEventListener("click", () => {
            navMenu.classList.remove("active");
            const icon = menuToggle.querySelector("i");
            if (icon) {
                icon.classList.add("fa-bars");
                icon.classList.remove("fa-xmark");
            }
        });
    });
}


// ===============================
// Navbar background on scroll
// ===============================

const header = document.querySelector(".header");

// ===============================
// Show Reveal Elements on Page Load
// ===============================

document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll(".reveal").forEach((el) => {

        el.classList.add("active");

    });

});


// ===============================
// Active Navigation Link
// ===============================

const navLinks = document.querySelectorAll(".nav-link");

const currentPage = window.location.pathname.split("/").pop();

navLinks.forEach(link => {

    const linkPage = link.getAttribute("href");

    if (linkPage === currentPage) {

        link.classList.add("active");

    }

});



// ===============================
// Typing Effect
// ===============================

const typingElement = document.getElementById("typing-text");

if (typingElement) {

    const words = [
        "Cyber Security Enthusiast",
        "Python Developer",
        "Web Developer",
        "Linux Learner"
    ];

    let wordIndex = 0;
    let charIndex = 0;
    let isDeleting = false;

    function typeEffect() {

        const currentWord = words[wordIndex];

        if (!isDeleting) {
            typingElement.textContent = currentWord.substring(0, charIndex++);
        } else {
            typingElement.textContent = currentWord.substring(0, charIndex--);
        }

        let speed = isDeleting ? 60 : 120;

        if (!isDeleting && charIndex > currentWord.length) {
            isDeleting = true;
            speed = 1500;
        }

        if (isDeleting && charIndex < 0) {
            isDeleting = false;
            wordIndex = (wordIndex + 1) % words.length;
            charIndex = 0;
        }

        setTimeout(typeEffect, speed);
    }

    typeEffect();
}

// ===============================
// Cyber Loader
// ===============================

const loadingMessages = [

    "Initializing Security...",

    "Loading Portfolio...",

    "Connecting Server...",

    "Access Granted ✔"

];

let messageIndex = 0;

const loadingText = document.getElementById("loading-text");

const messageInterval = setInterval(() => {

    if (loadingText && messageIndex < loadingMessages.length - 1){

        messageIndex++;

        loadingText.textContent = loadingMessages[messageIndex];

    }

},700);
window.addEventListener("load", () => {

    const loader = document.getElementById("loader");

    // Sirf pehli baar browser session me loader dikhao
    if (sessionStorage.getItem("loaderShown")) {

        if (loader) {
            loader.classList.add("hidden");
        }

        clearInterval(messageInterval);
        return;
    }

    sessionStorage.setItem("loaderShown", "true");

    setTimeout(() => {

        clearInterval(messageInterval);

        if (loader) {
            loader.classList.add("hidden");
        }

    }, 3000);

});






// ===============================
// Scroll Reveal Animation
// ===============================

const reveals = document.querySelectorAll(".reveal");

function revealElements() {

    reveals.forEach((element) => {

        const windowHeight = window.innerHeight;
        const elementTop = element.getBoundingClientRect().top;

        if (elementTop < windowHeight - 100) {
            element.classList.add("active");
        }

    });

}

window.addEventListener("scroll", revealElements);
window.addEventListener("load", revealElements);




window.addEventListener("scroll", () => {

    if (!header) return;

    if (window.scrollY > 50) {

        header.style.background = "rgba(15,23,42,0.95)";
        header.style.backdropFilter = "blur(15px)";

    } else {

        header.style.background = "rgba(15,23,42,0.85)";

    }

});


