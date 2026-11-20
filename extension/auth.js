(() => {
  "use strict";

  const API_BASE = "http://127.0.0.1:8000";

    const loginPanel = document.getElementById("login-panel");
    const accountPanel = document.getElementById("account-panel");

    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");

    const loginButton = document.getElementById("login-btn");
    const logoutButton = document.getElementById("logout-btn");

    const loginStatus = document.getElementById("login-status");
    const accountName = document.getElementById("account-name");
    const connectionStatus =
    document.getElementById("connection-status");
    const translatorPanel =
        document.getElementById("translator-panel");

    async function getToken() {
    const data = await chrome.storage.session.get("access_token");
    return data.access_token || null;
    }

    async function clearToken() {
    await chrome.storage.session.remove("access_token");
    }

    function showLoggedOut() {
    loginPanel.hidden = false;
        accountPanel.hidden = true;
        translatorPanel.hidden = true;

        passwordInput.value = "";
        window.dispatchEvent(new Event("urct:logout"));

    }

    function showLoggedIn(username) {
    loginPanel.hidden = true;
        accountPanel.hidden = false;
        translatorPanel.hidden = false;

        accountName.textContent = `Logged in: ${username}`;
        updateConnectionStatus();
        window.dispatchEvent(new Event("urct:login"));

    }

    async function authenticatedFetch(path, options = {}) {
        const token = await getToken();

        if (!token) {
            throw new Error("Login required");
        }

        return fetch(API_BASE + path, {
            ...options,
            headers: {
            ...(options.headers || {}),
            Authorization: `Bearer ${token}`
            }
        });
    }

    window.urctAuth = {authenticatedFetch };

    async function verifySession() {
    const token = await getToken();

    if (!token) {
        showLoggedOut();
        return;
    }

    try {
        const response = await authenticatedFetch("/auth/me");

        if (!response.ok) {
        await clearToken();
        showLoggedOut();
        return;
        }

        const user = await response.json();
        showLoggedIn(user.username);
    } catch {
        showLoggedOut();
        loginStatus.textContent = "Cannot reach URCT server";
    }
    }

    loginButton.addEventListener("click", async () => {
    loginButton.disabled = true;
    loginStatus.textContent = "Signing in...";

    try {
        const form = new URLSearchParams({
        username: usernameInput.value.trim(),
        password: passwordInput.value
        });

        const response = await fetch(API_BASE + "/auth/token", {
        method: "POST",
        headers: {
            "Content-Type":
            "application/x-www-form-urlencoded"
        },
        body: form
        });

        if (!response.ok) {
        throw new Error("Invalid credentials");
        }

        const result = await response.json();

        await chrome.storage.session.set({
        access_token: result.access_token
        });

        loginStatus.textContent = "";
        passwordInput.value = "";

        await verifySession();
    } catch (error) {
        loginStatus.textContent = error.message;
    } finally {
        loginButton.disabled = false;
    }
    });

    logoutButton.addEventListener("click", async () => {
    await clearToken();
    showLoggedOut();
    });

    // Used later for authenticated WebSocket ticket requests.
    async function requestWebSocketTicket(userId) {
    const response = await authenticatedFetch(
        "/auth/ws-ticket",
        {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_id: userId
        })
        }
    );

    if (!response.ok) {
        throw new Error("WebSocket ticket request failed");
    }

    return response.json();
    }

    const loginInputs = [
        usernameInput,
        passwordInput
    ];

    loginInputs.forEach((input) => {
        input.addEventListener("keydown", (event) => {
            if (
                event.key === "Enter" &&
                !event.isComposing &&
                !event.repeat
            ) {
                event.preventDefault();

                if (!loginButton.disabled) {
                    loginButton.click();
                }
            }
        });
    });


    async function updateConnectionStatus() {
    const data = await chrome.storage.session.get(
        "ws_status"
    );

    const status = data.ws_status || "disconnected";

    const labels = {
        connected: "WebSocket Connected",
        connecting: "Connecting to URCT server...",
        disconnected: "WebSocket Disconnected",
        connection_error: "WebSocket Connection Error"
    };

    connectionStatus.textContent =
        labels[status] || "Unknown status";
    }

    chrome.storage.onChanged.addListener(
    (changes, areaName) => {
        if (
        areaName === "session" &&
        changes.ws_status
        ) {
        updateConnectionStatus();
        }
    }
    );


    verifySession();
})();