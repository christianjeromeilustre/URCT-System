
const API_BASE = "http://127.0.0.1:8000";
const WS_BASE = "ws://127.0.0.1:8000";

const USER_ID = "owner";
const PING_INTERVAL = 20000;
const RETRY_INTERVAL = 3000;

let socket = null;
let pingTimer = null;
let retryTimer = null;
let connecting = false;
let stopped = false;
let connectionStatus = "disconnected";

// ----------------------------------------
// Connection status
// ----------------------------------------

function setStatus(status) {
  connectionStatus = status;

  // Never store access tokens or tickets
  // in the connection status.
  chrome.storage.session.set({
    ws_status: status
  });
}

function stopPing() {
  if (pingTimer !== null) {
    clearInterval(pingTimer);
    pingTimer = null;
  }
}

function startPing() {
  stopPing();

  pingTimer = setInterval(() => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: "ping"
      }));
    }
  }, PING_INTERVAL);
}

// ----------------------------------------
// Authentication
// ----------------------------------------

async function getAccessToken() {
  const data = await chrome.storage.session.get(
    "access_token"
  );

  return data.access_token || null;
}

async function getWebSocketTicket(token) {
  const response = await fetch(
    `${API_BASE}/auth/ws-ticket`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        user_id: USER_ID
      })
    }
  );

  if (response.status === 401) {
    await chrome.storage.session.remove(
      "access_token"
    );

    throw new Error("Session expired");
  }

  if (!response.ok) {
    throw new Error(
      `Ticket request failed: ${response.status}`
    );
  }

  return response.json();
}

// ----------------------------------------
// WebSocket connection
// ----------------------------------------

async function connectWebSocket() {
  if (connecting || stopped) {
    return;
  }

  if (
    socket &&
    (
      socket.readyState === WebSocket.OPEN ||
      socket.readyState === WebSocket.CONNECTING
    )
  ) {
    return;
  }

  connecting = true;
  setStatus("connecting");

  try {
    const token = await getAccessToken();

    if (!token || stopped) {
      setStatus("disconnected");
      return;
    }

    const ticketData = await getWebSocketTicket(
      token
    );

    if (stopped) {
      return;
    }

    const wsUrl =
      `${WS_BASE}/ws/${USER_ID}` +
      `?ticket=${encodeURIComponent(ticketData.ticket)}`;

    const ws = new WebSocket(wsUrl);
    socket = ws;

    ws.onopen = () => {
      if (stopped) {
        ws.close(1000, "Logout");
        return;
      }

      setStatus("connected");
      startPing();
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        if (message.type === "pong") {
          return;
        }

        // Message processing will be added later.
        console.log(
          "URCT WebSocket message type:",
          message.type
        );
      } catch {
        console.warn("Invalid WebSocket message");
      }
    };

    ws.onclose = async () => {
      if (socket !== ws) {
        return;
      }

      socket = null;
      stopPing();
      setStatus("disconnected");

      if (!stopped && await getAccessToken()) {
        scheduleReconnect();
      }
    };

    ws.onerror = () => {
      setStatus("connection_error");
      // onclose will handle reconnect.
    };

  } catch (error) {
    console.warn(
      "URCT connection error:",
      error.message
    );

    setStatus("connection_error");

    if (!stopped && await getAccessToken()) {
      scheduleReconnect();
    }

  } finally {
    connecting = false;
  }
}

// ----------------------------------------
// Reconnection
// ----------------------------------------

function scheduleReconnect() {
  if (retryTimer !== null || stopped) {
    return;
  }

  retryTimer = setTimeout(() => {
    retryTimer = null;
    connectWebSocket();
  }, RETRY_INTERVAL);
}

// ----------------------------------------
// Disconnect
// ----------------------------------------

function disconnectWebSocket() {
  stopped = true;
  stopPing();

  if (retryTimer !== null) {
    clearTimeout(retryTimer);
    retryTimer = null;
  }

  if (socket) {
    const ws = socket;
    socket = null;
    ws.close(1000, "User disconnected");
  }

  setStatus("disconnected");
}

// ----------------------------------------
// Login state changes
// ----------------------------------------

chrome.storage.onChanged.addListener(
  (changes, areaName) => {
    if (
      areaName !== "session" ||
      !changes.access_token
    ) {
      return;
    }

    if (changes.access_token.newValue) {
      stopped = false;
      connectWebSocket();
    } else {
      disconnectWebSocket();
    }
  }
);

// ----------------------------------------
// Popup status requests
// ----------------------------------------

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (message.type === "GET_WS_STATUS") {
      sendResponse({
        status: connectionStatus
      });
    }
  }
);

// ----------------------------------------
// Initialize after worker startup
// ----------------------------------------

(async () => {
  const token = await getAccessToken();

  if (token) {
    stopped = false;
    await connectWebSocket();
  } else {
    setStatus("disconnected");
  }
})();
