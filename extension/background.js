
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


        if (
          message.type === "archive_result" ||
          message.type === "archive_error"
        ) {
          chrome.storage.session.set({
            archive_last_result: message
          });

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


function sendArchiveTest(eventId) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return {
      ok: false,
      error: "WebSocket is not connected"
    };
  }

  socket.send(JSON.stringify({
    type: "archive_message",
    event_id: eventId,
    conversation_id: 2,
    contact_id: "f8d266c6-1113-4efb-8a56-e7ed9d5f1465",
    direction: "incoming",
    original_text: "Hello! This is a WebSocket history test.",
    translated_text: "안녕하세요! WebSocket 대화 기록 테스트입니다.",
    source_language: "en",
    target_language: "ko",
    engine_name: "test"
  }));

  return { ok: true, event_id: eventId };
}

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (message.type === "ARCHIVE_TEST") {
      const eventId = message.event_id;

      if (
        typeof eventId !== "string" ||
        !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(eventId)
      ) {
        sendResponse({
          ok: false,
          error: "Invalid event ID"
        });
        return;
      }

      sendResponse(sendArchiveTest(eventId));
    }
  }
);


async function getSelectedConversation() {
  const data = await chrome.storage.session.get([
    "access_token",
    "urct_selected_contact"
  ]);

  const contact = data.urct_selected_contact;
  const token = data.access_token;

  if (!token) {
    throw new Error("Login required");
  }

  if (!contact?.contact_id || !contact?.site_id) {
    throw new Error("Select a contact first");
  }

  const url =
    `${API_BASE}/history/contacts/` +
    `${encodeURIComponent(contact.contact_id)}/conversations`;

  const headers = {
    Authorization: `Bearer ${token}`
  };

  const response = await fetch(url, { headers });

  if (!response.ok) {
    throw new Error(`History API: ${response.status}`);
  }

  let conversations = await response.json();

  if (conversations.length === 0) {
    const created = await fetch(url, {
      method: "POST",
      headers
    });

    if (!created.ok) {
      throw new Error(
        `Create conversation: ${created.status}`
      );
    }

    conversations = [await created.json()];
  }

  const conversation = conversations[0];

  if (conversation.contact_id !== contact.contact_id) {
    throw new Error("Conversation contact mismatch");
  }

  return { contact, conversation };
}


async function sendSelectedArchiveTest(eventId) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    throw new Error("WebSocket is not connected");
  }

  const { contact, conversation } =
    await getSelectedConversation();

  if (!socket || socket.readyState !== WebSocket.OPEN) {
    throw new Error("WebSocket disconnected");
  }

  socket.send(JSON.stringify({
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
  }));

  return {
    ok: true,
    event_id: eventId,
    conversation_id: conversation.id
  };
}


chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (message?.type !== "ARCHIVE_SELECTED_TEST") {
      return;
    }

    const eventId = message.event_id;

    const uuidPattern =
      /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;

    if (
      typeof eventId !== "string" ||
      !uuidPattern.test(eventId)
    ) {
      sendResponse({
        ok: false,
        error: "Invalid event ID"
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

    return true;
  }
);


//
// URCT Universal ChatMessage v0.1
// This sends a history event, not a chat message
// to an external website.
//

function validateChatMessage(data) {
  if (!data || typeof data !== "object") {
    throw new Error("Invalid message.");
  }

  if (!["incoming", "outgoing"].includes(data.direction)) {
    throw new Error("Invalid direction.");
  }

  if (
    typeof data.original_text !== "string" ||
    !data.original_text.trim() ||
    data.original_text.length > 10000
  ) {
    throw new Error("Invalid original text.");
  }

  if (
    typeof data.translated_text !== "string" ||
    data.translated_text.length > 20000
  ) {
    throw new Error("Invalid translated text.");
  }

  if (
    typeof data.event_id !== "string" ||
    !/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i
      .test(data.event_id)
  ) {
    throw new Error("Invalid event ID.");
  }
}


async function archiveChatMessage(data) {
  validateChatMessage(data);

  if (!socket || socket.readyState !== WebSocket.OPEN) {
    throw new Error("WebSocket is not connected.");
  }

  const { contact, conversation } =
    await getSelectedConversation();

  const recipientLanguage =
    conversation.language || "en";

  const sourceLanguage = data.direction === "incoming"
    ? recipientLanguage
    : "ko";

  const targetLanguage = data.direction === "incoming"
    ? "ko"
    : recipientLanguage;

  const event = {
    type: "archive_message",
    event_id: data.event_id,

    contact_id: contact.contact_id,
    conversation_id: conversation.id,

    direction: data.direction,

    original_text: data.original_text.trim(),
    translated_text: data.translated_text.trim(),

    source_language: sourceLanguage,
    target_language: targetLanguage,

    engine_name: "manual"
  };

  if (!socket || socket.readyState !== WebSocket.OPEN) {
    throw new Error("WebSocket disconnected.");
  }

  socket.send(JSON.stringify(event));

  return {
    ok: true,
    event_id: event.event_id,
    contact_name: contact.display_name,
    conversation_id: conversation.id
  };
}


// Popup sends a message to the background worker.

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (message?.type !== "ARCHIVE_CHAT_MESSAGE") {
      return;
    }

    // Only accept this internal message from our extension.
    if (sender.id !== chrome.runtime.id || sender.tab) {
      sendResponse({
        ok: false,
        error: "Unauthorized message source."
      });
      return;
    }

    archiveChatMessage(message.payload)
      .then(sendResponse)
      .catch(error => {
        sendResponse({
          ok: false,
          error: error.message
        });
      });

    return true;
  }
);



