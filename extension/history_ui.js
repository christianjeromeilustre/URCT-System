
(() => {
  "use strict";

  const panel = document.getElementById("history-panel");
  const contactLabel = document.getElementById("history-contact");
  const status = document.getElementById("history-status");
  const conversationsBox = document.getElementById(
    "history-conversations"
  );
  const messagesBox = document.getElementById(
    "history-messages"
  );

  const refreshButton = document.getElementById(
    "history-refresh"
  );
  const newButton = document.getElementById("history-new");
  const closeButton = document.getElementById(
    "history-close"
  );

  let currentContactId = null;
  let currentSiteId = null;
  let currentConversationId = null;
  let requestVersion = 0;

  async function api(path, options = {}) {
    const response =
      await window.urctAuth.authenticatedFetch(
        path,
        options
      );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }

  function element(tag, text, className) {
    const node = document.createElement(tag);

    if (text !== undefined) {
      node.textContent = text;
    }

    if (className) {
      node.className = className;
    }

    return node;
  }

  function resetMessages() {
    messagesBox.replaceChildren();
    currentConversationId = null;
  }

  function closeHistory() {
    requestVersion++;
    panel.hidden = true;
    currentContactId = null;
    currentSiteId = null;
    resetMessages();
    conversationsBox.replaceChildren();
    status.textContent = "";
  }

  async function openHistory(siteId, contactId, contactName) {
    requestVersion++;

    currentSiteId = siteId;
    currentContactId = contactId;

    panel.hidden = false;
    contactLabel.textContent = `${contactName} · ${siteId}`;

    await loadConversations();
  }

  async function loadConversations() {
    if (!currentContactId) return;

    const version = ++requestVersion;
    const contactId = currentContactId;

    status.textContent = "Loading conversations...";
    conversationsBox.replaceChildren();
    resetMessages();

    try {
      const conversations = await api(
        `/history/contacts/${encodeURIComponent(contactId)}/conversations`
      );

      if (version !== requestVersion) return;

      if (conversations.length === 0) {
        conversationsBox.appendChild(
          element("p", "No conversations yet.")
        );
      }

      for (const conversation of conversations) {
        const box = element(
          "div",
          undefined,
          "history-conversation"
        );

        const heading = element(
          "strong",
          `Conversation #${conversation.id}`
        );

        const actions = element(
          "div",
          undefined,
          "history-actions"
        );

        const openButton = element(
          "button",
          "View Messages"
        );

        const deleteButton = element(
          "button",
          "Delete Conversation",
          "history-delete"
        );

        openButton.addEventListener("click", () => {
          loadMessages(conversation.id);
        });

        deleteButton.addEventListener("click", async () => {
          if (!confirm(
            `Delete Conversation #${conversation.id} and all its messages?`
          )) {
            return;
          }

          try {
            await api(
              `/history/conversations/${conversation.id}`,
              { method: "DELETE" }
            );

            status.textContent = "Conversation deleted.";
            await loadConversations();
          } catch (error) {
            status.textContent = error.message;
          }
        });

        actions.append(openButton, deleteButton);
        box.append(heading, actions);
        conversationsBox.appendChild(box);
      }

      status.textContent = `${conversations.length} conversation(s) found.`;

    } catch (error) {
      if (version === requestVersion) {
        status.textContent = error.message;
      }
    }
  }

  async function loadMessages(conversationId) {
    if (!currentContactId) return;

    const version = requestVersion;
    currentConversationId = conversationId;

    messagesBox.replaceChildren();
    status.textContent = "Loading messages...";

    try {
      const messages = await api(
        `/history/conversations/${conversationId}/messages`
      );

      if (
        version !== requestVersion ||
        currentConversationId !== conversationId
      ) {
        return;
      }

      messagesBox.appendChild(
        element("h3", `Conversation #${conversationId}`)
      );

      if (messages.length === 0) {
        messagesBox.appendChild(
          element("p", "No messages in this conversation.")
        );
      }

      for (const message of messages) {
        const card = element(
          "div",
          undefined,
          "history-message"
        );

        const label = element(
          "div",
          `#${message.id} · ${message.direction}`,
          "history-label"
        );

        const original = element(
          "div",
          message.original_text,
          "history-original"
        );

        const translation = element(
          "div",
          message.translated_text || "(No translation)",
          "history-translation"
        );

        const deleteButton = element(
          "button",
          "Delete Message",
          "history-delete"
        );

        deleteButton.addEventListener("click", async () => {
          if (!confirm(`Delete Message #${message.id}?`)) {
            return;
          }

          try {
            await api(
              `/history/messages/${message.id}`,
              { method: "DELETE" }
            );

            await loadMessages(conversationId);
          } catch (error) {
            status.textContent = error.message;
          }
        });

        card.append(
          label,
          original,
          translation,
          deleteButton
        );

        messagesBox.appendChild(card);
      }

      status.textContent = `${messages.length} message(s) loaded.`;

    } catch (error) {
      if (version === requestVersion) {
        status.textContent = error.message;
      }
    }
  }

  newButton.addEventListener("click", async () => {
    if (!currentContactId) return;

    newButton.disabled = true;

    try {
      const conversation = await api(
        `/history/contacts/${encodeURIComponent(currentContactId)}/conversations`,
        { method: "POST" }
      );

      await loadConversations();
      await loadMessages(conversation.id);

    } catch (error) {
      status.textContent = error.message;
    } finally {
      newButton.disabled = false;
    }
  });

  refreshButton.addEventListener(
    "click",
    loadConversations
  );

  closeButton.addEventListener(
    "click",
    closeHistory
  );

  window.addEventListener(
    "urct:logout",
    closeHistory
  );


    // -----------------------------------------
    // Refresh history when a new message is saved
    // -----------------------------------------

    window.addEventListener(
        "urct:history-updated",
        async () => {
            if (panel.hidden || !currentContactId) {
            return;
            }

            if (currentConversationId !== null) {
            await loadMessages(currentConversationId);
            } else {
            await loadConversations();
            }
        }
    );


    chrome.storage.onChanged.addListener(
    (changes, areaName) => {
        if (
        areaName !== "session" ||
        !changes.archive_last_result
        ) {
        return;
        }

        const result =
        changes.archive_last_result.newValue;

        if (
        result?.type !== "archive_result" ||
        result.status !== "saved"
        ) {
        return;
        }

        window.dispatchEvent(
        new Event("urct:history-updated")
        );
    }
    );



  window.urctHistory = {
    openHistory,
    closeHistory
  };
})();
