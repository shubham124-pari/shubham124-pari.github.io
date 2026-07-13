// =====================================================
// dashboard.html logic
// Relies on globals exposed by auth.js: skpApiRequest,
// skpMapUser, skpGetSessionUser, skpSignOut,
// skpVerifySession, skpRenderNavAuthState, SKP_TOKEN_KEY.
// =====================================================

document.addEventListener("DOMContentLoaded", async () => {

    const guard = document.getElementById("dashboardGuard");
    const shell = document.getElementById("dashboardShell");
    const dashSignInBtn = document.getElementById("dashboardSignInBtn");

    const dashAvatar = document.getElementById("dashAvatar");
    const dashName = document.getElementById("dashName");
    const dashMeta = document.getElementById("dashMeta");

    const tabs = document.querySelectorAll("#dashboardTabs .account-tab");
    const panels = document.querySelectorAll(".account-panel");

    let currentUser = null;

    // ---------------- helpers ----------------

    function getInitials(name) {
        return (name || "?").trim().split(/\s+/).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
    }

    function formatDate(iso) {
        if (!iso) return "";
        try {
            return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
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
        // relativePath already looks like "/uploads/photos/xyz.jpg" from the
        // backend; just prepend the backend origin (strip the trailing /api).
        const origin = SKP_API_BASE.replace(/\/api\/?$/, "");
        return origin + relativePath;
    }
    window.skpFileUrl = fileUrl;

    // ---------------- guard: must be signed in ----------------

    if (dashSignInBtn) {
        dashSignInBtn.addEventListener("click", () => {
            const btn = document.getElementById("signInBtn");
            if (btn) btn.click();
        });
    }

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
        loadProfile();
        loadProjects();
        loadUploadsStatus();
        loadMessages();
        loadOverview();
        loadSkills();
        loadEducation();
        loadExperience();
        loadNotifications();
        loadActivity();
        applySettingsUI();
    }

    function renderHeader(user) {
        dashAvatar.textContent = getInitials(user.name);
        dashName.textContent = user.name;
        dashMeta.textContent = user.email + " · Member since " + formatDate(user.createdAt);
    }

    // ---------------- tabs ----------------

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.toggle("active", t === tab));
            const targetId = tab.dataset.dtab + "Panel";
            panels.forEach((p) => p.classList.toggle("active", p.id === targetId));
        });
    });

    // ================================================
    // PROFILE
    // ================================================

    const profileForm = document.getElementById("profileForm");
    const profileNameInput = document.getElementById("profileNameInput");
    const profileBioInput = document.getElementById("profileBioInput");
    const profileAlert = document.getElementById("profileAlert");

    function loadProfile() {
        if (!currentUser) return;
        profileNameInput.value = currentUser.name || "";
        profileBioInput.value = currentUser.bio || "";
    }

    if (profileForm) {
        profileForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(profileAlert);
            const btn = profileForm.querySelector("button[type=submit]");
            const original = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = "<span>Saving...</span>";

            try {
                const data = await skpApiRequest("/user/profile", {
                    method: "PUT",
                    auth: true,
                    body: { name: profileNameInput.value.trim(), bio: profileBioInput.value.trim() },
                });
                const user = skpMapUser(data.user);
                localStorage.setItem(SKP_USER_CACHE_KEY, JSON.stringify(user));
                currentUser = user;
                renderHeader(user);
                if (window.skpRenderNavAuthState) window.skpRenderNavAuthState();
                showAlert(profileAlert, "success", "Profile updated.");
            } catch (err) {
                showAlert(profileAlert, "error", err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = original;
            }
        });
    }

    // ================================================
    // PROJECTS
    // ================================================

    const addProjectToggle = document.getElementById("addProjectToggle");
    const projectForm = document.getElementById("projectForm");
    const projectIdField = document.getElementById("projectIdField");
    const projectImageInput = document.getElementById("projectImageInput");
    const projectSubmitLabel = document.getElementById("projectSubmitLabel");
    const projectGrid = document.getElementById("projectGrid");
    const projectsEmpty = document.getElementById("projectsEmpty");
    const projectsAlert = document.getElementById("projectsAlert");

    if (addProjectToggle) {
        addProjectToggle.addEventListener("click", () => {
            const willShow = projectForm.style.display === "none";
            resetProjectForm();
            projectForm.style.display = willShow ? "flex" : "none";
        });
    }

    function resetProjectForm() {
        projectForm.reset();
        projectIdField.value = "";
        projectSubmitLabel.textContent = "Save Project";
    }

    async function loadProjects() {
        try {
            const data = await skpApiRequest("/projects", { auth: true });
            renderProjects(data.projects || []);
        } catch (err) {
            showAlert(projectsAlert, "error", err.message);
        }
    }

    function renderProjects(projects) {
        projectGrid.innerHTML = "";
        projectsEmpty.style.display = projects.length === 0 ? "block" : "none";

        projects.forEach((p) => {
            const card = document.createElement("div");
            card.className = "project-card";

            const img = p.image
                ? `<img class="project-card-thumb" src="${escapeHtml(fileUrl(p.image))}" alt="${escapeHtml(p.title)}">`
                : "";

            const links = (p.github || p.demo)
                ? `<div class="project-card-links">
                        ${p.github ? `<a href="${escapeHtml(p.github)}" target="_blank" rel="noopener noreferrer"><i class="fa-brands fa-github"></i> Code</a>` : ""}
                        ${p.demo ? `<a href="${escapeHtml(p.demo)}" target="_blank" rel="noopener noreferrer"><i class="fa-solid fa-arrow-up-right-from-square"></i> Live</a>` : ""}
                   </div>`
                : "";

            card.innerHTML =
                img +
                `<h3>${escapeHtml(p.title)}</h3>` +
                `<p>${escapeHtml(p.description || "")}</p>` +
                links +
                `<div class="project-card-actions">
                    <button type="button" class="edit-project-btn"><i class="fa-solid fa-pen"></i> Edit</button>
                    <button type="button" class="danger delete-project-btn"><i class="fa-solid fa-trash"></i> Delete</button>
                 </div>`;

            card.querySelector(".edit-project-btn").addEventListener("click", () => {
                projectIdField.value = p.id;
                projectForm.querySelector('[name="title"]').value = p.title || "";
                projectForm.querySelector('[name="description"]').value = p.description || "";
                projectForm.querySelector('[name="github"]').value = p.github || "";
                projectForm.querySelector('[name="demo"]').value = p.demo || "";
                projectSubmitLabel.textContent = "Update Project";
                projectForm.style.display = "flex";
                projectForm.scrollIntoView({ behavior: "smooth", block: "center" });
            });

            card.querySelector(".delete-project-btn").addEventListener("click", async () => {
                if (!confirm(`Delete "${p.title}"? This can't be undone.`)) return;
                try {
                    await skpApiRequest(`/projects/${p.id}`, { method: "DELETE", auth: true });
                    loadProjects();
                } catch (err) {
                    showAlert(projectsAlert, "error", err.message);
                }
            });

            projectGrid.appendChild(card);
        });
    }

    if (projectForm) {
        projectForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(projectsAlert);
            const btn = projectForm.querySelector("button[type=submit]");
            const original = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = "<span>Saving...</span>";

            try {
                let imagePath = null;

                if (projectImageInput.files && projectImageInput.files[0]) {
                    const fd = new FormData();
                    fd.append("file", projectImageInput.files[0]);
                    const uploadRes = await skpApiRequest("/user/upload/project", {
                        method: "POST", auth: true, isForm: true, body: fd,
                    });
                    imagePath = uploadRes.image;
                }

                const payload = {
                    title: projectForm.querySelector('[name="title"]').value.trim(),
                    description: projectForm.querySelector('[name="description"]').value.trim(),
                    github: projectForm.querySelector('[name="github"]').value.trim(),
                    demo: projectForm.querySelector('[name="demo"]').value.trim(),
                };
                if (imagePath) payload.image = imagePath;

                const projectId = projectIdField.value;
                if (projectId) {
                    await skpApiRequest(`/projects/${projectId}`, { method: "PUT", auth: true, body: payload });
                } else {
                    await skpApiRequest("/projects", { method: "POST", auth: true, body: payload });
                }

                showAlert(projectsAlert, "success", "Project saved.");
                projectForm.style.display = "none";
                resetProjectForm();
                loadProjects();
            } catch (err) {
                showAlert(projectsAlert, "error", err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = original;
            }
        });
    }

    // ================================================
    // UPLOADS (photo / resume / certificate)
    // ================================================

    const photoInput = document.getElementById("photoInput");
    const coverInput = document.getElementById("coverInput");
    const resumeInput = document.getElementById("resumeInput");
    const certificateInput = document.getElementById("certificateInput");
    const photoStatus = document.getElementById("photoStatus");
    const coverStatus = document.getElementById("coverStatus");
    const resumeStatus = document.getElementById("resumeStatus");
    const certificateStatus = document.getElementById("certificateStatus");
    const uploadsAlert = document.getElementById("uploadsAlert");

    function loadUploadsStatus() {
        if (!currentUser) return;
        photoStatus.innerHTML = currentUser.profile_photo
            ? `<a href="${escapeHtml(fileUrl(currentUser.profile_photo))}" target="_blank" rel="noopener noreferrer">View current photo</a>`
            : "No photo uploaded";
        coverStatus.innerHTML = currentUser.cover_photo
            ? `<a href="${escapeHtml(fileUrl(currentUser.cover_photo))}" target="_blank" rel="noopener noreferrer">View current cover</a>`
            : "No cover uploaded";
        resumeStatus.innerHTML = currentUser.resume
            ? `<a href="${escapeHtml(fileUrl(currentUser.resume))}" target="_blank" rel="noopener noreferrer">View current resume</a>`
            : "No resume uploaded";
        certificateStatus.innerHTML = currentUser.certificate
            ? `<a href="${escapeHtml(fileUrl(currentUser.certificate))}" target="_blank" rel="noopener noreferrer">View current certificate</a>`
            : "No certificate uploaded";
    }

    async function handleUpload(kind, file, statusEl, userField) {
        clearAlert(uploadsAlert);
        try {
            const fd = new FormData();
            fd.append("file", file);
            const res = await skpApiRequest(`/user/upload/${kind}`, {
                method: "POST", auth: true, isForm: true, body: fd,
            });
            currentUser[userField] = res[userField];
            localStorage.setItem(SKP_USER_CACHE_KEY, JSON.stringify(currentUser));
            loadUploadsStatus();
            renderOverviewHeader();
            showAlert(uploadsAlert, "success", "Uploaded successfully.");
        } catch (err) {
            showAlert(uploadsAlert, "error", err.message);
        }
    }

    if (photoInput) {
        photoInput.addEventListener("change", () => {
            if (photoInput.files[0]) handleUpload("photo", photoInput.files[0], photoStatus, "profile_photo");
        });
    }
    if (coverInput) {
        coverInput.addEventListener("change", () => {
            if (coverInput.files[0]) handleUpload("cover", coverInput.files[0], coverStatus, "cover_photo");
        });
    }
    if (resumeInput) {
        resumeInput.addEventListener("change", () => {
            if (resumeInput.files[0]) handleUpload("resume", resumeInput.files[0], resumeStatus, "resume");
        });
    }
    if (certificateInput) {
        certificateInput.addEventListener("change", () => {
            if (certificateInput.files[0]) handleUpload("certificate", certificateInput.files[0], certificateStatus, "certificate");
        });
    }

    // ================================================
    // SUPPORT / MESSAGES
    // ================================================

    const complaintForm = document.getElementById("complaintForm");
    const supportAlert = document.getElementById("supportAlert");
    const messageList = document.getElementById("messageList");

    async function loadMessages() {
        try {
            const data = await skpApiRequest("/contact/mine", { auth: true });
            renderMessages(data.messages || []);
        } catch (err) {
            // Non-fatal — just leave the "no messages yet" placeholder.
        }
    }

    function renderMessages(msgs) {
        messageList.innerHTML = "";
        if (msgs.length === 0) {
            messageList.innerHTML = '<li class="message-empty">No messages sent yet.</li>';
            return;
        }
        msgs.forEach((m) => {
            const li = document.createElement("li");
            li.className = "message-item";
            const statusClass = m.status === "resolved" ? "sent" : "queued";
            const statusLabel = m.status ? m.status[0].toUpperCase() + m.status.slice(1) : "New";
            li.innerHTML =
                `<div class="message-item-top">
                    <span class="message-category">${escapeHtml(m.subject ? "Support" : "Message")}</span>
                    <span class="message-status ${statusClass}">${escapeHtml(statusLabel)}</span>
                 </div>
                 <p class="message-subject">${escapeHtml(m.subject || "")}</p>
                 <p class="message-body">${escapeHtml(m.message)}</p>
                 <span class="message-date">${escapeHtml(formatDate(m.date))}</span>`;
            messageList.appendChild(li);
        });
    }

    if (complaintForm) {
        complaintForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(supportAlert);
            if (!currentUser) return;

            const btn = complaintForm.querySelector("button[type=submit]");
            const original = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = "<span>Sending...</span>";

            try {
                const category = complaintForm.querySelector('[name="category"]').value;
                const subject = complaintForm.querySelector('[name="subject"]').value.trim();
                const message = complaintForm.querySelector('[name="message"]').value.trim();

                await skpApiRequest("/contact", {
                    method: "POST",
                    auth: true,
                    body: {
                        name: currentUser.name,
                        email: currentUser.email,
                        subject: `[${category}] ${subject}`,
                        message,
                    },
                });

                showAlert(supportAlert, "success", "Your message has been sent. Thank you!");
                complaintForm.reset();
                loadMessages();
            } catch (err) {
                showAlert(supportAlert, "error", err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = original;
            }
        });
    }

    // ================================================
    // SETTINGS (password + delete account)
    // ================================================

    const passwordForm = document.getElementById("passwordForm");
    const settingsAlert = document.getElementById("settingsAlert");
    const deleteForm = document.getElementById("deleteForm");
    const deleteAlert = document.getElementById("deleteAlert");

    if (passwordForm) {
        passwordForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(settingsAlert);
            const btn = passwordForm.querySelector("button[type=submit]");
            const original = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = "<span>Updating...</span>";

            try {
                const data = new FormData(passwordForm);
                const newPassword = data.get("new_password");
                const confirm = data.get("confirm");
                if (newPassword !== confirm) throw new Error("New passwords do not match.");

                await skpApiRequest("/user/settings/password", {
                    method: "PUT",
                    auth: true,
                    body: {
                        current_password: data.get("current_password"),
                        new_password: newPassword,
                        confirm: confirm,
                    },
                });
                showAlert(settingsAlert, "success", "Password changed successfully.");
                passwordForm.reset();
            } catch (err) {
                showAlert(settingsAlert, "error", err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = original;
            }
        });
    }

    if (deleteForm) {
        deleteForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(deleteAlert);

            if (!confirm("This will permanently delete your account. Are you absolutely sure?")) return;

            const btn = deleteForm.querySelector("button[type=submit]");
            const original = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = "<span>Deleting...</span>";

            try {
                const data = new FormData(deleteForm);
                await skpApiRequest("/user/account", {
                    method: "DELETE",
                    auth: true,
                    body: { password: data.get("password") },
                });
                skpSignOut();
                window.location.href = "index.html";
            } catch (err) {
                showAlert(deleteAlert, "error", err.message);
                btn.disabled = false;
                btn.innerHTML = original;
            }
        });
    }

    // ================================================
    // OVERVIEW / DASHBOARD ANALYTICS
    // ================================================

    const overviewCoverImg = document.getElementById("overviewCoverImg");
    const overviewAvatarImg = document.getElementById("overviewAvatarImg");
    const overviewAvatarFallback = document.getElementById("overviewAvatarFallback");
    const overviewName = document.getElementById("overviewName");
    const overviewBio = document.getElementById("overviewBio");
    const overviewCompletenessText = document.getElementById("overviewCompletenessText");

    function renderOverviewHeader() {
        if (!currentUser) return;
        if (currentUser.cover_photo) {
            overviewCoverImg.src = fileUrl(currentUser.cover_photo);
            overviewCoverImg.style.display = "block";
        } else {
            overviewCoverImg.style.display = "none";
        }
        if (currentUser.profile_photo) {
            overviewAvatarImg.src = fileUrl(currentUser.profile_photo);
            overviewAvatarImg.style.display = "block";
            overviewAvatarFallback.style.display = "none";
        } else {
            overviewAvatarImg.style.display = "none";
            overviewAvatarFallback.style.display = "flex";
            overviewAvatarFallback.textContent = getInitials(currentUser.name);
        }
        overviewName.textContent = currentUser.name || "";
        overviewBio.textContent = currentUser.bio || "No bio added yet — head to the Profile tab to add one.";
    }

    async function loadOverview() {
        renderOverviewHeader();
        try {
            const data = await skpApiRequest("/user/dashboard/summary", { auth: true });
            document.getElementById("statProjects").textContent = data.projects;
            document.getElementById("statSkills").textContent = data.skills;
            document.getElementById("statChats").textContent = data.chat_conversations;
            document.getElementById("statAi").textContent = data.ai_conversations;
            document.getElementById("statSupport").textContent = data.support_messages;
            document.getElementById("statUnread").textContent = data.unread_notifications;
            updateNotifBadge(data.unread_notifications);
            overviewCompletenessText.textContent = data.profile_complete
                ? "Your profile looks complete — photo and bio are both set."
                : "Add a profile photo and a short bio to complete your profile.";
        } catch (err) {
            // Non-fatal — stats just stay at 0.
        }
    }

    // ================================================
    // SKILLS
    // ================================================

    const skillForm = document.getElementById("skillForm");
    const skillNameInput = document.getElementById("skillNameInput");
    const skillLevelInput = document.getElementById("skillLevelInput");
    const skillLevelValue = document.getElementById("skillLevelValue");
    const skillGrid = document.getElementById("skillGrid");
    const skillsEmpty = document.getElementById("skillsEmpty");
    const skillsAlert = document.getElementById("skillsAlert");

    if (skillLevelInput) {
        skillLevelInput.addEventListener("input", () => { skillLevelValue.textContent = skillLevelInput.value; });
    }

    async function loadSkills() {
        try {
            const data = await skpApiRequest("/user/skills", { auth: true });
            renderSkills(data.skills || []);
        } catch (err) {
            showAlert(skillsAlert, "error", err.message);
        }
    }

    function renderSkills(skills) {
        skillGrid.innerHTML = "";
        skillsEmpty.style.display = skills.length === 0 ? "block" : "none";
        skills.forEach((s) => {
            const chip = document.createElement("div");
            chip.className = "skill-chip";
            chip.innerHTML = `
                <span class="skill-chip-name">${escapeHtml(s.name)}</span>
                <span class="skill-chip-bar"><span style="width:${s.level * 20}%"></span></span>
                <button type="button" class="skill-chip-remove" aria-label="Remove skill"><i class="fa-solid fa-xmark"></i></button>
            `;
            chip.querySelector(".skill-chip-remove").addEventListener("click", async () => {
                try {
                    await skpApiRequest(`/user/skills/${s.id}`, { method: "DELETE", auth: true });
                    loadSkills();
                    loadOverview();
                } catch (err) {
                    showAlert(skillsAlert, "error", err.message);
                }
            });
            skillGrid.appendChild(chip);
        });
    }

    if (skillForm) {
        skillForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(skillsAlert);
            const name = skillNameInput.value.trim();
            if (!name) return;
            try {
                await skpApiRequest("/user/skills", {
                    method: "POST", auth: true,
                    body: { name, level: parseInt(skillLevelInput.value, 10) },
                });
                skillForm.reset();
                skillLevelValue.textContent = "3";
                loadSkills();
                loadOverview();
            } catch (err) {
                showAlert(skillsAlert, "error", err.message);
            }
        });
    }

    // ================================================
    // BACKGROUND: EDUCATION
    // ================================================

    const addEducationToggle = document.getElementById("addEducationToggle");
    const educationForm = document.getElementById("educationForm");
    const educationIdField = document.getElementById("educationIdField");
    const educationSubmitLabel = document.getElementById("educationSubmitLabel");
    const educationList = document.getElementById("educationList");
    const educationEmpty = document.getElementById("educationEmpty");
    const backgroundAlert = document.getElementById("backgroundAlert");

    if (addEducationToggle) {
        addEducationToggle.addEventListener("click", () => {
            const willShow = educationForm.style.display === "none";
            educationForm.reset();
            educationIdField.value = "";
            educationSubmitLabel.textContent = "Save";
            educationForm.style.display = willShow ? "flex" : "none";
        });
    }

    async function loadEducation() {
        try {
            const data = await skpApiRequest("/user/education", { auth: true });
            renderEducation(data.education || []);
        } catch (err) {
            showAlert(backgroundAlert, "error", err.message);
        }
    }

    function renderEducation(items) {
        educationList.innerHTML = "";
        educationEmpty.style.display = items.length === 0 ? "block" : "none";
        items.forEach((ed) => {
            const li = document.createElement("div");
            li.className = "timeline-item";
            const years = [ed.start_year, ed.end_year || "Present"].filter(Boolean).join(" – ");
            li.innerHTML = `
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                    <h5>${escapeHtml(ed.school)}</h5>
                    <p class="timeline-sub">${escapeHtml([ed.degree, ed.field].filter(Boolean).join(", "))}</p>
                    <span class="timeline-years">${escapeHtml(years)}</span>
                    ${ed.description ? `<p class="timeline-desc">${escapeHtml(ed.description)}</p>` : ""}
                    <div class="timeline-actions">
                        <button type="button" class="edit-btn"><i class="fa-solid fa-pen"></i></button>
                        <button type="button" class="danger delete-btn"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
            `;
            li.querySelector(".edit-btn").addEventListener("click", () => {
                educationIdField.value = ed.id;
                educationForm.querySelector('[name="school"]').value = ed.school || "";
                educationForm.querySelector('[name="degree"]').value = ed.degree || "";
                educationForm.querySelector('[name="field"]').value = ed.field || "";
                educationForm.querySelector('[name="start_year"]').value = ed.start_year || "";
                educationForm.querySelector('[name="end_year"]').value = ed.end_year || "";
                educationForm.querySelector('[name="description"]').value = ed.description || "";
                educationSubmitLabel.textContent = "Update";
                educationForm.style.display = "flex";
                educationForm.scrollIntoView({ behavior: "smooth", block: "center" });
            });
            li.querySelector(".delete-btn").addEventListener("click", async () => {
                if (!confirm(`Remove "${ed.school}"?`)) return;
                try {
                    await skpApiRequest(`/user/education/${ed.id}`, { method: "DELETE", auth: true });
                    loadEducation();
                } catch (err) {
                    showAlert(backgroundAlert, "error", err.message);
                }
            });
            educationList.appendChild(li);
        });
    }

    if (educationForm) {
        educationForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(backgroundAlert);
            const fd = new FormData(educationForm);
            const payload = {
                school: fd.get("school")?.trim(),
                degree: fd.get("degree")?.trim(),
                field: fd.get("field")?.trim(),
                start_year: fd.get("start_year") || null,
                end_year: fd.get("end_year") || null,
                description: fd.get("description")?.trim(),
            };
            try {
                const id = educationIdField.value;
                if (id) {
                    await skpApiRequest(`/user/education/${id}`, { method: "PUT", auth: true, body: payload });
                } else {
                    await skpApiRequest("/user/education", { method: "POST", auth: true, body: payload });
                }
                educationForm.style.display = "none";
                loadEducation();
            } catch (err) {
                showAlert(backgroundAlert, "error", err.message);
            }
        });
    }

    // ================================================
    // BACKGROUND: EXPERIENCE
    // ================================================

    const addExperienceToggle = document.getElementById("addExperienceToggle");
    const experienceForm = document.getElementById("experienceForm");
    const experienceIdField = document.getElementById("experienceIdField");
    const experienceSubmitLabel = document.getElementById("experienceSubmitLabel");
    const experienceCurrentCheckbox = document.getElementById("experienceCurrentCheckbox");
    const experienceEndDate = document.getElementById("experienceEndDate");
    const experienceList = document.getElementById("experienceList");
    const experienceEmpty = document.getElementById("experienceEmpty");

    if (addExperienceToggle) {
        addExperienceToggle.addEventListener("click", () => {
            const willShow = experienceForm.style.display === "none";
            experienceForm.reset();
            experienceIdField.value = "";
            experienceSubmitLabel.textContent = "Save";
            experienceForm.style.display = willShow ? "flex" : "none";
        });
    }

    if (experienceCurrentCheckbox) {
        experienceCurrentCheckbox.addEventListener("change", () => {
            experienceEndDate.disabled = experienceCurrentCheckbox.checked;
            if (experienceCurrentCheckbox.checked) experienceEndDate.value = "";
        });
    }

    async function loadExperience() {
        try {
            const data = await skpApiRequest("/user/experience", { auth: true });
            renderExperience(data.experience || []);
        } catch (err) {
            showAlert(backgroundAlert, "error", err.message);
        }
    }

    function renderExperience(items) {
        experienceList.innerHTML = "";
        experienceEmpty.style.display = items.length === 0 ? "block" : "none";
        items.forEach((ex) => {
            const li = document.createElement("div");
            li.className = "timeline-item";
            const range = `${formatDate(ex.start_date) || ""} – ${ex.is_current ? "Present" : (formatDate(ex.end_date) || "")}`;
            li.innerHTML = `
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                    <h5>${escapeHtml(ex.role)} · ${escapeHtml(ex.company)}</h5>
                    <span class="timeline-years">${escapeHtml(range)}</span>
                    ${ex.description ? `<p class="timeline-desc">${escapeHtml(ex.description)}</p>` : ""}
                    <div class="timeline-actions">
                        <button type="button" class="edit-btn"><i class="fa-solid fa-pen"></i></button>
                        <button type="button" class="danger delete-btn"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
            `;
            li.querySelector(".edit-btn").addEventListener("click", () => {
                experienceIdField.value = ex.id;
                experienceForm.querySelector('[name="company"]').value = ex.company || "";
                experienceForm.querySelector('[name="role"]').value = ex.role || "";
                experienceForm.querySelector('[name="start_date"]').value = ex.start_date ? ex.start_date.slice(0, 10) : "";
                experienceForm.querySelector('[name="end_date"]').value = ex.end_date ? ex.end_date.slice(0, 10) : "";
                experienceCurrentCheckbox.checked = ex.is_current;
                experienceEndDate.disabled = ex.is_current;
                experienceForm.querySelector('[name="description"]').value = ex.description || "";
                experienceSubmitLabel.textContent = "Update";
                experienceForm.style.display = "flex";
                experienceForm.scrollIntoView({ behavior: "smooth", block: "center" });
            });
            li.querySelector(".delete-btn").addEventListener("click", async () => {
                if (!confirm(`Remove "${ex.role} at ${ex.company}"?`)) return;
                try {
                    await skpApiRequest(`/user/experience/${ex.id}`, { method: "DELETE", auth: true });
                    loadExperience();
                } catch (err) {
                    showAlert(backgroundAlert, "error", err.message);
                }
            });
            experienceList.appendChild(li);
        });
    }

    if (experienceForm) {
        experienceForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlert(backgroundAlert);
            const fd = new FormData(experienceForm);
            const payload = {
                company: fd.get("company")?.trim(),
                role: fd.get("role")?.trim(),
                start_date: fd.get("start_date") || null,
                end_date: fd.get("end_date") || null,
                is_current: !!fd.get("is_current"),
                description: fd.get("description")?.trim(),
            };
            try {
                const id = experienceIdField.value;
                if (id) {
                    await skpApiRequest(`/user/experience/${id}`, { method: "PUT", auth: true, body: payload });
                } else {
                    await skpApiRequest("/user/experience", { method: "POST", auth: true, body: payload });
                }
                experienceForm.style.display = "none";
                loadExperience();
            } catch (err) {
                showAlert(backgroundAlert, "error", err.message);
            }
        });
    }

    // ================================================
    // NOTIFICATION CENTER
    // ================================================

    const notificationList = document.getElementById("notificationList");
    const notificationsEmpty = document.getElementById("notificationsEmpty");
    const notificationsAlert = document.getElementById("notificationsAlert");
    const markAllReadBtn = document.getElementById("markAllReadBtn");
    const notifTabBadge = document.getElementById("notifTabBadge");

    const NOTIF_ICONS = { chat: "fa-comments", contact: "fa-headset", account: "fa-shield-halved", system: "fa-circle-info" };

    function updateNotifBadge(count) {
        if (!notifTabBadge) return;
        notifTabBadge.textContent = count;
        notifTabBadge.style.display = count > 0 ? "inline-block" : "none";
    }

    async function loadNotifications() {
        try {
            const data = await skpApiRequest("/user/notifications", { auth: true });
            renderNotifications(data.notifications || []);
            updateNotifBadge(data.unread_count || 0);
        } catch (err) {
            showAlert(notificationsAlert, "error", err.message);
        }
    }

    function renderNotifications(items) {
        notificationList.innerHTML = "";
        notificationsEmpty.style.display = items.length === 0 ? "block" : "none";
        items.forEach((n) => {
            const li = document.createElement("li");
            li.className = "notification-item" + (n.is_read ? "" : " unread");
            li.innerHTML = `
                <i class="fa-solid ${NOTIF_ICONS[n.type] || "fa-bell"}"></i>
                <div class="notification-body">
                    <h5>${escapeHtml(n.title)}</h5>
                    ${n.body ? `<p>${escapeHtml(n.body)}</p>` : ""}
                    <span class="notification-time">${escapeHtml(formatDate(n.created_at))}</span>
                </div>
            `;
            li.addEventListener("click", async () => {
                if (n.is_read) return;
                try {
                    await skpApiRequest(`/user/notifications/${n.id}/read`, { method: "PUT", auth: true });
                    n.is_read = true;
                    li.classList.remove("unread");
                    loadOverview();
                } catch (err) { /* non-fatal */ }
            });
            notificationList.appendChild(li);
        });
    }

    if (markAllReadBtn) {
        markAllReadBtn.addEventListener("click", async () => {
            try {
                await skpApiRequest("/user/notifications/read-all", { method: "PUT", auth: true });
                loadNotifications();
                loadOverview();
            } catch (err) {
                showAlert(notificationsAlert, "error", err.message);
            }
        });
    }

    // ================================================
    // ACTIVITY TIMELINE
    // ================================================

    const activityList = document.getElementById("activityList");
    const activityEmpty = document.getElementById("activityEmpty");

    const ACTIVITY_LABELS = {
        login: "Signed in", signup: "Created account", profile_update: "Updated profile",
        password_change: "Changed password", settings_update: "Updated settings",
        file_upload: "Uploaded a file", project_create: "Created a project",
        project_update: "Updated a project", project_delete: "Deleted a project",
        skill_add: "Added a skill", education_add: "Added education",
        experience_add: "Added experience",
    };

    async function loadActivity() {
        try {
            const data = await skpApiRequest("/user/activity", { auth: true });
            renderActivity(data.activity || []);
        } catch (err) {
            // non-fatal
        }
    }

    function renderActivity(items) {
        activityList.innerHTML = "";
        activityEmpty.style.display = items.length === 0 ? "block" : "none";
        items.forEach((a) => {
            const li = document.createElement("div");
            li.className = "timeline-item";
            const label = ACTIVITY_LABELS[a.action] || a.action;
            li.innerHTML = `
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                    <h5>${escapeHtml(label)}</h5>
                    ${a.meta ? `<p class="timeline-desc">${escapeHtml(a.meta)}</p>` : ""}
                    <span class="timeline-years">${escapeHtml(formatDate(a.created_at))}</span>
                </div>
            `;
            activityList.appendChild(li);
        });
    }

    // ================================================
    // SETTINGS: theme / privacy / notification toggles
    // ================================================

    const themeToggleGroup = document.getElementById("themeToggleGroup");
    const privacyToggleGroup = document.getElementById("privacyToggleGroup");
    const notifyEmailToggle = document.getElementById("notifyEmailToggle");
    const notifyChatToggle = document.getElementById("notifyChatToggle");

    function applySettingsUI() {
        if (!currentUser) return;
        themeToggleGroup?.querySelectorAll(".toggle-pill").forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.theme === (currentUser.theme || "dark"));
        });
        privacyToggleGroup?.querySelectorAll(".toggle-pill").forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.visibility === (currentUser.profile_visibility || "public"));
        });
        if (notifyEmailToggle) notifyEmailToggle.checked = currentUser.notify_email !== false;
        if (notifyChatToggle) notifyChatToggle.checked = currentUser.notify_chat !== false;
        document.body.classList.toggle("theme-light", currentUser.theme === "light");
    }

    themeToggleGroup?.addEventListener("click", async (e) => {
        const btn = e.target.closest(".toggle-pill[data-theme]");
        if (!btn) return;
        try {
            const data = await skpApiRequest("/user/settings/theme", {
                method: "PUT", auth: true, body: { theme: btn.dataset.theme },
            });
            currentUser = skpMapUser(data.user);
            localStorage.setItem(SKP_USER_CACHE_KEY, JSON.stringify(currentUser));
            applySettingsUI();
            showAlert(settingsAlert, "success", "Theme updated.");
        } catch (err) {
            showAlert(settingsAlert, "error", err.message);
        }
    });

    privacyToggleGroup?.addEventListener("click", async (e) => {
        const btn = e.target.closest(".toggle-pill[data-visibility]");
        if (!btn) return;
        try {
            const data = await skpApiRequest("/user/settings/privacy", {
                method: "PUT", auth: true, body: { profile_visibility: btn.dataset.visibility },
            });
            currentUser = skpMapUser(data.user);
            localStorage.setItem(SKP_USER_CACHE_KEY, JSON.stringify(currentUser));
            applySettingsUI();
            showAlert(settingsAlert, "success", "Privacy setting updated.");
        } catch (err) {
            showAlert(settingsAlert, "error", err.message);
        }
    });

    async function saveNotificationPrefs() {
        try {
            const data = await skpApiRequest("/user/settings/notifications", {
                method: "PUT", auth: true,
                body: { notify_email: notifyEmailToggle.checked, notify_chat: notifyChatToggle.checked },
            });
            currentUser = skpMapUser(data.user);
            localStorage.setItem(SKP_USER_CACHE_KEY, JSON.stringify(currentUser));
            showAlert(settingsAlert, "success", "Notification preferences saved.");
        } catch (err) {
            showAlert(settingsAlert, "error", err.message);
        }
    }
    notifyEmailToggle?.addEventListener("change", saveNotificationPrefs);
    notifyChatToggle?.addEventListener("change", saveNotificationPrefs);

    boot();
});
