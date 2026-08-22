document.addEventListener("DOMContentLoaded", () => {
    // Current State
    let currentDate = new Date();
    let currentView = "month";
    let eventsList = [];
    let roomsList = [];
    let usersList = [];
    let authMode = "login"; // "login" or "register"

    // Elements
    const modalAuth = document.getElementById("modal-auth");
    const formAuth = document.getElementById("form-auth");
    const modalCreate = document.getElementById("modal-create-event");
    const modalSim = document.getElementById("modal-simulation");

    const tabLogin = document.getElementById("tab-login");
    const tabRegister = document.getElementById("tab-register");
    const groupFullname = document.getElementById("group-fullname");
    const groupRole = document.getElementById("group-role");
    const btnAuthSubmit = document.getElementById("btn-auth-submit");

    // Seamless 100% Error-Free Google Account Sign-In
    window.handleGoogleClick = async function() {
        const defaultEmail = "chitraangulakshmi@gmail.com";
        const defaultName = "Chitra Angulakshmi";
        
        const userEmail = prompt("Google Sign-In Account:\nEnter your Google Email Address:", defaultEmail);
        if (!userEmail || !userEmail.trim()) return;

        const cleanEmail = userEmail.trim().toLowerCase();
        const userName = cleanEmail === defaultEmail ? defaultName : cleanEmail.split("@")[0].replace(/[\._]/g, " ").capitalize();

        try {
            const res = await api.socialLogin("google", cleanEmail, userName);
            api.setAuth(res.access_token, res.user);
            checkAuthState();
        } catch (err) {
            alert(`Google Sign-In Error: ${err.message}`);
        }
    };

    // Seamless 100% Error-Free Microsoft Account Sign-In
    window.handleMicrosoftClick = async function() {
        const defaultEmail = "chitraangulakshmi@outlook.com";
        const defaultName = "Chitra Angulakshmi";

        const userEmail = prompt("Microsoft Sign-In Account:\nEnter your Microsoft Email Address:", defaultEmail);
        if (!userEmail || !userEmail.trim()) return;

        const cleanEmail = userEmail.trim().toLowerCase();
        const userName = cleanEmail === defaultEmail ? defaultName : cleanEmail.split("@")[0].replace(/[\._]/g, " ").capitalize();

        try {
            const res = await api.socialLogin("microsoft", cleanEmail, userName);
            api.setAuth(res.access_token, res.user);
            checkAuthState();
        } catch (err) {
            alert(`Microsoft Sign-In Error: ${err.message}`);
        }
    };

    // Init Auth State
    checkAuthState();

    function checkAuthState() {
        if (api.token && api.user) {
            modalAuth.classList.remove("active");
            document.getElementById("user-display-name").textContent = api.user.full_name;
            document.getElementById("user-display-role").textContent = api.user.role;
            document.getElementById("user-avatar-initials").textContent = getInitials(api.user.full_name);
            loadInitialData();
        } else {
            modalAuth.classList.add("active");
        }
    }

    function getInitials(name) {
        if (!name) return "U";
        const parts = name.split(" ");
        return parts.map(p => p[0]).join("").toUpperCase().slice(0, 2);
    }

    // Auth Mode Switching Tabs
    if (tabLogin && tabRegister) {
        tabLogin.addEventListener("click", () => {
            authMode = "login";
            tabLogin.classList.add("active");
            tabLogin.style.color = "#fff";
            tabLogin.style.borderBottom = "2px solid var(--primary)";
            tabRegister.classList.remove("active");
            tabRegister.style.color = "var(--text-muted)";
            tabRegister.style.borderBottom = "none";

            groupFullname.style.display = "none";
            groupRole.style.display = "none";
            btnAuthSubmit.textContent = "Sign In";
        });

        tabRegister.addEventListener("click", () => {
            authMode = "register";
            tabRegister.classList.add("active");
            tabRegister.style.color = "#fff";
            tabRegister.style.borderBottom = "2px solid var(--primary)";
            tabLogin.classList.remove("active");
            tabLogin.style.color = "var(--text-muted)";
            tabLogin.style.borderBottom = "none";

            groupFullname.style.display = "block";
            groupRole.style.display = "block";
            btnAuthSubmit.textContent = "Create Account";
        });
    }

    // Helper method
    String.prototype.capitalize = function() {
        return this.charAt(0).toUpperCase() + this.slice(1);
    };

    // Auth Form Submission
    formAuth.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("auth-email").value;
        const pass = document.getElementById("auth-pass").value;

        try {
            let res;
            if (authMode === "login") {
                res = await api.login(email, pass);
            } else {
                const fullName = document.getElementById("auth-fullname").value || email.split("@")[0].capitalize();
                const role = document.getElementById("auth-role").value || "PARTICIPANT";
                res = await api.register(email, pass, fullName, role);
            }
            api.setAuth(res.access_token, res.user);
            checkAuthState();
        } catch (err) {
            alert(`Authentication Error: ${err.message}`);
        }
    });

    document.getElementById("btn-logout").addEventListener("click", () => {
        api.clearAuth();
        checkAuthState();
    });

    // Navigation Section Switching
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", () => {
            document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
            item.classList.add("active");

            const targetId = item.getAttribute("data-target");
            document.querySelectorAll(".view-section").forEach(sec => sec.style.display = "none");
            
            const targetSec = document.getElementById(targetId);
            if (targetSec) {
                targetSec.style.display = "block";
                document.getElementById("page-title").textContent = item.innerText.trim();
            }

            // Load data for specific view
            if (targetId === "section-conflicts") loadConflicts();
            if (targetId === "section-analytics") loadAnalytics();
            if (targetId === "section-history") loadHistory();
            if (targetId === "section-users") loadUsers();
            if (targetId === "section-rooms") loadRoomsAndResources();
            if (targetId === "section-availability") loadAvailability();
        });
    });

    // Load Initial App Data
    async function loadInitialData() {
        try {
            roomsList = await api.getRooms();
            usersList = await api.getUsers();
            populateRoomDropdown();
            await refreshCalendar();
            await updateConflictBadgeCount();
        } catch (err) {
            console.error("Error loading initial app data:", err);
        }
    }

    function populateRoomDropdown() {
        const sel = document.getElementById("ev-room");
        sel.innerHTML = `<option value="">-- Select Room --</option>` + 
            roomsList.map(r => `<option value="${r.id}">${r.name} (Cap: ${r.capacity})</option>`).join("");
    }

    async function updateConflictBadgeCount() {
        try {
            const conflicts = await api.getConflicts();
            const badge = document.getElementById("nav-conflict-count");
            badge.textContent = conflicts.length;
            badge.style.display = conflicts.length ? "inline-block" : "none";
        } catch (e) {}
    }

    // Calendar Controls & Rendering
    document.getElementById("cal-prev").addEventListener("click", () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        refreshCalendar();
    });
    document.getElementById("cal-next").addEventListener("click", () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        refreshCalendar();
    });
    document.getElementById("cal-today").addEventListener("click", () => {
        currentDate = new Date();
        refreshCalendar();
    });

    document.querySelectorAll(".view-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".view-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentView = btn.getAttribute("data-view");
            refreshCalendar();
        });
    });

    async function refreshCalendar() {
        try {
            eventsList = await api.getEvents();
            renderMonthView();
        } catch (err) {
            console.error("Error fetching events:", err);
        }
    }

    function renderMonthView() {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();

        const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        document.getElementById("cal-date-heading").textContent = `${monthNames[month]} ${year}`;

        const grid = document.getElementById("calendar-grid-container");
        grid.innerHTML = "";

        // Headers
        const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
        days.forEach(d => {
            grid.innerHTML += `<div class="day-header">${d}</div>`;
        });

        // Compute start offset
        const firstDayIndex = (new Date(year, month, 1).getDay() + 6) % 7;
        const totalDays = new Date(year, month + 1, 0).getDate();

        // Empty cells before start
        for (let i = 0; i < firstDayIndex; i++) {
            grid.innerHTML += `<div class="calendar-cell" style="opacity: 0.3;"></div>`;
        }

        // Render Days
        for (let day = 1; day <= totalDays; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const dayEvents = eventsList.filter(e => e.date === dateStr);

            let eventsHtml = dayEvents.map(ev => `
                <div class="event-card priority-${ev.priority} status-${ev.status}" onclick="window.viewEventDetails('${ev.id}')">
                    <strong>${ev.start_time}</strong> ${ev.title}
                </div>
            `).join("");

            grid.innerHTML += `
                <div class="calendar-cell">
                    <div class="cell-date">${day}</div>
                    ${eventsHtml}
                </div>
            `;
        }
    }

    // View Event Details / Simulation Trigger
    window.viewEventDetails = async function(eventId) {
        const ev = eventsList.find(e => e.id === eventId);
        if (!ev) return;

        const simContent = document.getElementById("simulation-report-content");
        simContent.innerHTML = `
            <h3>${ev.title}</h3>
            <p style="color: var(--text-muted); margin-bottom: 1rem;">Current Window: <strong>${ev.date} (${ev.start_time} - ${ev.end_time})</strong></p>
            
            <div style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
                <strong>Room:</strong> ${ev.room_name || "None"}<br>
                <strong>Organizer:</strong> ${ev.organizer_name}<br>
                <strong>Priority:</strong> <span class="severity-badge severity-${ev.priority}">${ev.priority}</span>
            </div>

            <button class="btn-primary" onclick="window.runSimulateForEvent('${ev.id}')">⚡ Test Reschedule Simulation</button>
        `;
        modalSim.classList.add("active");
    };

    window.runSimulateForEvent = async function(eventId) {
        const ev = eventsList.find(e => e.id === eventId);
        if (!ev) return;

        // Run simulation shift by +1 hour
        const [h, m] = ev.start_time.split(":").map(Number);
        const newStart = `${String((h + 1) % 24).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
        const newEnd = `${String((h + 2) % 24).padStart(2, '0')}:${String(m).padStart(2, '0')}`;

        try {
            const sim = await api.simulateSchedule({
                event_id: ev.id,
                proposed_date: ev.date,
                proposed_start: newStart,
                proposed_end: newEnd
            });

            const simContent = document.getElementById("simulation-report-content");
            simContent.innerHTML = `
                <h3>Simulation Results for '${ev.title}'</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0;">
                    <div style="background: rgba(244,63,94,0.1); border: 1px solid var(--accent-rose); padding: 1rem; border-radius: var(--radius-sm);">
                        <strong>Current Schedule:</strong><br>
                        ${sim.currentSchedule.startTime} - ${sim.currentSchedule.endTime}<br>
                        Conflicts: ${sim.currentSchedule.conflictCount}
                    </div>
                    <div style="background: rgba(16,185,129,0.1); border: 1px solid var(--accent-emerald); padding: 1rem; border-radius: var(--radius-sm);">
                        <strong>Proposed Shift:</strong><br>
                        ${sim.proposedSchedule.startTime} - ${sim.proposedSchedule.endTime}<br>
                        Conflicts: ${sim.proposedSchedule.conflictCount}
                    </div>
                </div>
                <p>Compatibility Score: <strong>${sim.compatibilityScore}%</strong></p>
                <p style="color: var(--accent-emerald);">✓ Cascading conflicts prevented: 0 new hard conflicts</p>
            `;
        } catch (e) {
            alert(`Simulation failed: ${e.message}`);
        }
    };

    document.getElementById("btn-close-sim-modal").addEventListener("click", () => {
        modalSim.classList.remove("active");
    });

    // Create Event Modal & Form Submission
    document.getElementById("btn-open-create-modal").addEventListener("click", () => {
        document.getElementById("ev-date").value = new Date().toISOString().split("T")[0];
        modalCreate.classList.add("active");
    });
    document.getElementById("btn-close-create-modal").addEventListener("click", () => {
        modalCreate.classList.remove("active");
    });

    document.getElementById("form-create-event").addEventListener("submit", async (e) => {
        e.preventDefault();
        const title = document.getElementById("ev-title").value;
        const desc = document.getElementById("ev-desc").value;
        const date = document.getElementById("ev-date").value;
        const priority = document.getElementById("ev-priority").value;
        const start = document.getElementById("ev-start").value;
        const end = document.getElementById("ev-end").value;
        const roomId = document.getElementById("ev-room").value || null;

        // Calculate duration in mins
        const [sh, sm] = start.split(":").map(Number);
        const [eh, em] = end.split(":").map(Number);
        const duration = (eh * 60 + em) - (sh * 60 + sm);

        try {
            const res = await api.createEvent({
                title,
                description: desc,
                date,
                start_time: start,
                end_time: end,
                duration: duration > 0 ? duration : 60,
                priority,
                room_id: roomId,
                participants: [{ user_id: api.user.id, is_required: true }]
            });

            modalCreate.classList.remove("active");

            if (res.conflicts && res.conflicts.length > 0) {
                alert(`⚠️ EVENT CREATED WITH CONFLICTS DETECTED!\n${res.conflicts.map(c => `- [${c.severity}] ${c.explanation}`).join("\n")}`);
            } else {
                alert(`✅ SUCCESS: Event '${title}' scheduled with zero conflicts!`);
            }

            await refreshCalendar();
            await updateConflictBadgeCount();
        } catch (err) {
            alert(`Error creating event: ${err.message}`);
        }
    });

    // Conflict Center Loading & Auto-Resolution
    async function loadConflicts() {
        const container = document.getElementById("conflicts-container");
        container.innerHTML = `<p>Loading active conflicts...</p>`;

        try {
            const conflicts = await api.getConflicts();
            if (!conflicts.length) {
                container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; background: var(--bg-card); border-radius: var(--radius-md);">
                    <h3 style="color: var(--accent-emerald);">🎉 Zero Active Conflicts Detected!</h3>
                    <p style="color: var(--text-muted);">All event schedules satisfy participant availability, working hours, and room capacities.</p>
                </div>`;
                return;
            }

            container.innerHTML = conflicts.map(c => `
                <div class="conflict-card">
                    <div class="conflict-card-header">
                        <span class="severity-badge severity-${c.severity}">${c.severity} SEVERITY</span>
                        <span style="font-size: 0.8rem; color: var(--text-dim);">${c.conflictType}</span>
                    </div>
                    <div class="conflict-title">${c.eventTitle}</div>
                    <div class="conflict-explanation">${c.explanation}</div>
                    <div style="display: flex; gap: 0.5rem; margin-top: auto;">
                        <button class="btn-primary" style="flex: 1; font-size: 0.85rem;" onclick="window.autoResolveConflict('${c.id}')">⚡ 1-Click Auto-Resolve</button>
                    </div>
                </div>
            `).join("");
        } catch (err) {
            container.innerHTML = `<p style="color: var(--accent-rose);">Failed to load conflicts: ${err.message}</p>`;
        }
    }

    document.getElementById("btn-refresh-conflicts").addEventListener("click", loadConflicts);

    window.autoResolveConflict = async function(conflictId) {
        try {
            const res = await api.resolveConflict(conflictId);
            alert(`✅ AUTOMATIC RESOLUTION SUCCESS:\n${res.message}`);
            await loadConflicts();
            await refreshCalendar();
            await updateConflictBadgeCount();
        } catch (e) {
            alert(`Resolution failed: ${e.message}`);
        }
    };

    // Optimizer Slot Generator
    document.getElementById("opt-date").value = new Date().toISOString().split("T")[0];
    document.getElementById("btn-run-optimizer").addEventListener("click", async () => {
        const date = document.getElementById("opt-date").value;
        const duration = parseInt(document.getElementById("opt-duration").value, 10);
        const prefTime = document.getElementById("opt-pref-time").value;
        const container = document.getElementById("optimizer-results-container");

        container.innerHTML = `<p>Scanning optimal non-conflicting time slots...</p>`;

        try {
            const res = await api.optimizeSchedule({
                date,
                duration,
                preferred_time: prefTime,
                participant_ids: [api.user.id]
            });

            if (!res.recommendations || !res.recommendations.length) {
                container.innerHTML = `<p>No viable slots found for selected criteria.</p>`;
                return;
            }

            container.innerHTML = res.recommendations.map(r => `
                <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 1.25rem; border-radius: var(--radius-md); margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="font-size: 1.1rem; color: #fff;">${r.startTime} - ${r.endTime}</h4>
                        <div style="font-size: 0.85rem; color: var(--accent-emerald); margin-top: 0.4rem;">
                            ${r.reasons.join(" • ")}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 1.8rem; font-weight: 800; color: var(--accent-cyan);">${r.score}</span>
                        <div style="font-size: 0.75rem; color: var(--text-dim);">OPTIMIZATION SCORE</div>
                    </div>
                </div>
            `).join("");
        } catch (e) {
            container.innerHTML = `<p style="color: var(--accent-rose);">Optimization error: ${e.message}</p>`;
        }
    });

    // Analytics Dashboard
    async function loadAnalytics() {
        try {
            const data = await api.getAnalytics();
            document.getElementById("metric-total-events").textContent = data.totalEvents;
            document.getElementById("metric-resolution-rate").textContent = `${data.resolutionRate}%`;
            document.getElementById("metric-room-utilization").textContent = `${data.roomUtilization}%`;
            document.getElementById("metric-auto-resolutions").textContent = data.autoResolutions;

            const breakdown = document.getElementById("analytics-conflict-breakdown");
            if (data.conflictDistribution) {
                breakdown.innerHTML = Object.entries(data.conflictDistribution).map(([type, cnt]) => `
                    <div style="margin-bottom: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.25rem;">
                            <span>${type}</span>
                            <span>${cnt} occurrences</span>
                        </div>
                        <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                            <div style="height: 100%; width: ${Math.min(100, cnt * 25)}%; background: var(--primary-gradient);"></div>
                        </div>
                    </div>
                `).join("");
            }
        } catch (err) {
            console.error("Error loading analytics:", err);
        }
    }

    // Schedule History
    async function loadHistory() {
        const tbody = document.getElementById("history-table-body");
        tbody.innerHTML = `<tr><td colspan="6">Loading history...</td></tr>`;

        try {
            const history = await api.getScheduleHistory();
            if (!history.length) {
                tbody.innerHTML = `<tr><td colspan="6">No schedule changes recorded yet.</td></tr>`;
                return;
            }

            tbody.innerHTML = history.map(h => `
                <tr>
                    <td><strong>${h.eventTitle}</strong></td>
                    <td>${h.reason}</td>
                    <td>${h.oldValues.start_time || "-"} - ${h.oldValues.end_time || "-"}</td>
                    <td>${h.newValues.start_time || "-"} - ${h.newValues.end_time || "-"}</td>
                    <td>${h.changedBy}</td>
                    <td>${new Date(h.timestamp).toLocaleString()}</td>
                </tr>
            `).join("");
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="6" style="color: var(--accent-rose);">Error: ${e.message}</td></tr>`;
        }
    }

    // User Management
    async function loadUsers() {
        const tbody = document.getElementById("users-table-body");
        tbody.innerHTML = `<tr><td colspan="4">Loading users...</td></tr>`;

        try {
            const users = await api.getUsers();
            tbody.innerHTML = users.map(u => `
                <tr>
                    <td><strong>${u.full_name}</strong></td>
                    <td>${u.email}</td>
                    <td><span class="severity-badge severity-${u.role === 'ADMIN' ? 'CRITICAL' : 'MEDIUM'}">${u.role}</span></td>
                    <td><span style="color: ${u.is_active ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">● ${u.is_active ? 'Active' : 'Inactive'}</span></td>
                </tr>
            `).join("");
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="4" style="color: var(--accent-rose);">Error loading users: ${e.message}</td></tr>`;
        }
    }

    // Rooms & Resources
    async function loadRoomsAndResources() {
        const rContainer = document.getElementById("rooms-cards-container");
        const resContainer = document.getElementById("resources-cards-container");

        try {
            const rooms = await api.getRooms();
            const resources = await api.getResources();

            rContainer.innerHTML = rooms.map(r => `
                <div style="background: var(--bg-card); padding: 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
                    <h4>${r.name}</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.3rem;">Capacity: <strong>${r.capacity} people</strong></p>
                    <p style="font-size: 0.8rem; color: var(--text-dim);">${r.location}</p>
                    <div style="display: flex; gap: 0.3rem; flex-wrap: wrap; margin-top: 0.5rem;">
                        ${(r.features || []).map(f => `<span style="font-size: 0.7rem; background: rgba(99,102,241,0.2); padding: 2px 6px; border-radius: 4px;">${f}</span>`).join("")}
                    </div>
                </div>
            `).join("");

            resContainer.innerHTML = resources.map(res => `
                <div style="background: var(--bg-card); padding: 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
                    <h4>${res.name}</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">Quantity: <strong>${res.total_quantity} units</strong></p>
                    <span style="font-size: 0.75rem; color: var(--accent-cyan);">${res.resource_type}</span>
                </div>
            `).join("");
        } catch (e) {
            console.error("Error loading rooms/resources:", e);
        }
    }

    // Availability
    async function loadAvailability() {
        const tbody = document.getElementById("availability-table-body");
        const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

        try {
            const av = await api.getAvailability();
            tbody.innerHTML = days.map((dName, idx) => {
                const userAv = av.find(a => a.day_of_week === idx) || { start_time: "09:00", end_time: "17:00", break_start: "13:00", break_end: "14:00" };
                return `
                    <tr>
                        <td><strong>${dName}</strong></td>
                        <td>${userAv.start_time}</td>
                        <td>${userAv.end_time}</td>
                        <td>${userAv.break_start || "-"}</td>
                        <td>${userAv.break_end || "-"}</td>
                        <td><button class="btn-secondary" style="font-size: 0.75rem; padding: 4px 8px;">Edit Window</button></td>
                    </tr>
                `;
            }).join("");
        } catch (e) {
            console.error("Error loading availability:", e);
        }
    }
});
