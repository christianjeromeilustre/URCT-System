
(() => {
  "use strict";

  const newButton = document.getElementById(
    "archive-test-new"
  );

  const repeatButton = document.getElementById(
    "archive-test-repeat"
  );

  const status = document.getElementById(
    "archive-test-status"
  );

  let lastEventId = null;

  repeatButton.disabled = true;

  async function sendEvent(eventId) {
    status.textContent = "Sending event...";

    try {
      const response = await chrome.runtime.sendMessage({
        type: "ARCHIVE_SELECTED_TEST",
        event_id: eventId
      });

      if (!response?.ok) {
        throw new Error(
          response?.error || "Request failed"
        );
      }

      status.textContent =
        "Event sent. Waiting for server result...";

    } catch (error) {
      status.textContent = error.message;
    }
  }

  newButton.addEventListener("click", async () => {
    lastEventId = crypto.randomUUID();
    repeatButton.disabled = false;

    await sendEvent(lastEventId);
  });

  repeatButton.addEventListener("click", async () => {
    if (!lastEventId) {
      return;
    }

    await sendEvent(lastEventId);
  });

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

      if (!result || result.event_id !== lastEventId) {
        return;
      }

      if (result.type === "archive_result") {
        status.textContent =
          `Archive: ${result.status}` +
          (result.message_id
            ? ` · Message #${result.message_id}`
            : "");
      } else {
        status.textContent =
          `Archive error: ${result.message}`;
      }
    }
  );

  window.addEventListener("urct:logout", () => {
    lastEventId = null;
    repeatButton.disabled = true;
    status.textContent = "Not logged in.";
  });
})();
