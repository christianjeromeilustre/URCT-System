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
        await chrome.storage.session.remove
        ([
            "access_token"
        ,
            "urct_selected_contact"
        ,
            "archive_last_result"
        ]);
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


// ----------------------------------------
// Contact-based archive test
// ----------------------------------------

async function getSelectedConversation() {
  const saved = await chrome.storage.session.get(
    "urct_selected_contact"
  );

  const contact = saved.urct_selected_contact;

  if (!contact?.contact_id || !contact?.site_id) {
    throw new Error("Select a contact first.");
  }

  const tokenData = await chrome.storage.session.get(
    "access_token"
  );

  if (!tokenData.access_token) {
    throw new Error("Login required.");
  }

  const headers = {
    Authorization: `Bearer ${tokenData.access_token}`
  };

  const contactId = encodeURIComponent(
    contact.contact_id
  );

  const url =
    `${API_BASE}/history/contacts/` +
    `${contactId}/conversations`;

  const response = await fetch(url, { headers });

  if (!response.ok) {
    throw new Error(
      `Conversation lookup failed: ${response.status}`
    );
  }

  let conversations = await response.json();

  // Use the most recent conversation,
  // or create one if none exists.
  if (conversations.length === 0) {
    const createResponse = await fetch(url, {
      method: "POST",
      headers
    });

    if (!createResponse.ok) {
      throw new Error(
        `Conversation creation failed: ${createResponse.status}`
      );
    }

    conversations = [await createResponse.json()];
  }

  return {
    contact,
    conversation: conversations[0]
  };
}


async function sendSelectedArchiveTest(eventId) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    throw new Error("WebSocket is not connected.");
  }

  const { contact, conversation } =
    await getSelectedConversation();

  // Confirm the socket is still connected after
  // asynchronous API requests.
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    throw new Error("WebSocket disconnected.");
  }

  const event = {
    type: "archive_message",
    event_id: eventId,
    conversation_id: conversation.id,
    contact_id: contact.contact_id,
    direction: "incoming",
    original_text:
      "Hello! This message belongs to the selected contact.",
    translated_text:
      "안녕하세요! 이 메시지는 선택한 상대방의 기록입니다.",
    source_language: "en",
    target_language: "ko",
    engine_name: "test"
  };

  socket.send(JSON.stringify(event));

  return {
    ok: true,
    event_id: eventId,
    contact_name: contact.display_name,
    conversation_id: conversation.id
  };
}


// Handle the new test request.
// The existing ARCHIVE_TEST handler stays unchanged
// until this version is verified.

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (message?.type !== "ARCHIVE_SELECTED_TEST") {
      return;
    }

    const eventId = message.event_id;

    if (
      typeof eventId !== "string" ||
      !/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(
        eventId
      )
    ) {
      sendResponse({
        ok: false,
        error: "Invalid event ID."
      });
      return;
    }

    sendSelectedArchiveTest(eventId)
      .then(sendResponse)
      .catch(error => {
        sendResponse({
          ok: false,
          error: error.message
        });
      });

    // Required for an asynchronous sendResponse.
    return true;
  }
);
