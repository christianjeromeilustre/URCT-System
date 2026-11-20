
(() => {
  "use strict";

  const direction = document.getElementById("chat-direction");
  const original = document.getElementById("chat-original");
  const translated = document.getElementById("chat-translated");
  const saveButton = document.getElementById("chat-save");
  const status = document.getElementById("chat-save-status");

  let pendingEventId = null;

    const requiredElements = {
    direction,
    original,
    translated,
    saveButton,
    status
    };

    for (const [name, element] of Object.entries(requiredElements)) {
    if (!element) {
        throw new Error(
        `URCT ChatMessage: Missing HTML element '${name}'`
        );
    }
}

  saveButton.addEventListener("click", async () => {
    if (pendingEventId) {
      status.textContent = "A request is already pending.";
      return;
    }

    if (!original.value.trim()) {
      status.textContent = "Enter the original message.";
      return;
    }

    if (!translated.value.trim()) {
      status.textContent = "Enter the translated message.";
      return;
    }

    const eventId = crypto.randomUUID();

    pendingEventId = eventId;
    saveButton.disabled = true;
    status.textContent = "Sending...";

    const payload = {
      event_id: eventId,
      direction: direction.value,
      original_text: original.value,
      translated_text: translated.value
    };

    try {
      const response = await chrome.runtime.sendMessage({
        type: "ARCHIVE_CHAT_MESSAGE",
        payload
      });

      if (!response?.ok) {
        throw new Error(
          response?.error || "Message request failed."
        );
      }

      status.textContent = "Waiting for SQLite confirmation...";

    } catch (error) {
      pendingEventId = null;
      saveButton.disabled = false;
      status.textContent = error.message;
    }
  });

  chrome.storage.onChanged.addListener(
    (changes, areaName) => {
      if (
        areaName !== "session" ||
        !changes.archive_last_result ||
        !pendingEventId
      ) {
        return;
      }

      const result = changes.archive_last_result.newValue;

      if (!result || result.event_id !== pendingEventId) {
        return;
      }

      pendingEventId = null;
      saveButton.disabled = false;

      if (result.type === "archive_result") {
        status.textContent =
          `Archive: ${result.status}` +
          (result.message_id
            ? ` · Message #${result.message_id}`
            : "");

        if (result.status === "saved") {
          window.dispatchEvent(
            new Event("urct:history-updated")
          );
        }
      } else {
        status.textContent =
          `Archive error: ${result.message || "Unknown error"}`;
      }
    }
  );

  window.addEventListener("urct:logout", () => {
    pendingEventId = null;
    saveButton.disabled = false;
    original.value = "";
    translated.value = "";
    status.textContent = "Login required.";
  });
})();
