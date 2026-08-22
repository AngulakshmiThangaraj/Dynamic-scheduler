const API_BASE_URL = window.location.origin.includes("5000") 
    ? "http://localhost:5000/api" 
    : "/api";

class ApiClient {
    constructor() {
        this.token = localStorage.getItem("auth_token") || null;
        this.user = JSON.parse(localStorage.getItem("auth_user") || "null");
    }

    setAuth(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem("auth_token", token);
        localStorage.setItem("auth_user", JSON.stringify(user));
    }

    clearAuth() {
        this.token = null;
        this.user = null;
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
    }

    async request(endpoint, options = {}) {
        const headers = {
            "Content-Type": "application/json",
            ...options.headers
        };

        if (this.token) {
            headers["Authorization"] = `Bearer ${this.token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const res = await fetch(`${API_BASE_URL}${endpoint}`, config);
            const data = await res.json();
            
            if (!res.ok) {
                if (res.status === 401) {
                    this.clearAuth();
                    window.dispatchEvent(new Event("auth_logout"));
                }
                const errorMsg = data.detail || (data.error && data.error.message) || "API Request Failed";
                throw new Error(errorMsg);
            }

            return data;
        } catch (err) {
            console.error(`API Error [${endpoint}]:`, err);
            throw err;
        }
    }

    // Auth
    login(email, password) {
        return this.request("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });
    }

    register(email, password, full_name, role) {
        return this.request("/auth/register", {
            method: "POST",
            body: JSON.stringify({ email, password, full_name, role })
        });
    }

    getMe() {
        return this.request("/auth/me");
    }

    // Events
    getEvents(date = null, status = null) {
        let q = [];
        if (date) q.push(`date=${date}`);
        if (status) q.push(`status=${status}`);
        const query = q.length ? `?${q.join("&")}` : "";
        return this.request(`/events${query}`);
    }

    getEvent(id) {
        return this.request(`/events/${id}`);
    }

    createEvent(eventData) {
        return this.request("/events", {
            method: "POST",
            body: JSON.stringify(eventData)
        });
    }

    updateEvent(id, eventData) {
        return this.request(`/events/${id}`, {
            method: "PUT",
            body: JSON.stringify(eventData)
        });
    }

    deleteEvent(id) {
        return this.request(`/events/${id}`, {
            method: "DELETE"
        });
    }

    // Scheduling & Simulation
    optimizeSchedule(data) {
        return this.request("/schedule/optimize", {
            method: "POST",
            body: JSON.stringify(data)
        });
    }

    simulateSchedule(data) {
        return this.request("/schedule/simulate", {
            method: "POST",
            body: JSON.stringify(data)
        });
    }

    // Conflicts
    getConflicts() {
        return this.request("/conflicts");
    }

    resolveConflict(conflictId) {
        return this.request("/conflicts/resolve", {
            method: "POST",
            body: JSON.stringify({ conflict_id: conflictId })
        });
    }

    // Users, Rooms, Resources
    getUsers() {
        return this.request("/users");
    }

    getRooms() {
        return this.request("/rooms");
    }

    getResources() {
        return this.request("/resources");
    }

    // Availability
    getAvailability() {
        return this.request("/availability");
    }

    setAvailability(data) {
        return this.request("/availability", {
            method: "POST",
            body: JSON.stringify(data)
        });
    }

    // Analytics
    getAnalytics() {
        return this.request("/analytics");
    }

    // Notifications
    getNotifications() {
        return this.request("/notifications");
    }

    markNotificationsRead() {
        return this.request("/notifications/read", {
            method: "POST"
        });
    }

    // History & Audit
    getScheduleHistory() {
        return this.request("/schedule-history");
    }

    getAuditLogs() {
        return this.request("/audit-logs");
    }
}

const api = new ApiClient();
