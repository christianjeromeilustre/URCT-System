
(() => {
  "use strict";

  const panel = document.getElementById(
    "contact-detail-panel"
  );

  const title = document.getElementById(
    "detail-contact-name"
  );

  const language = document.getElementById(
    "detail-language"
  );

  const mode = document.getElementById(
    "detail-mode"
  );

  const style = document.getElementById(
    "detail-style"
  );

  const autoDetect = document.getElementById(
    "detail-auto-detect"
  );

  const saveButton = document.getElementById(
    "detail-save"
  );

  const closeButton = document.getElementById(
    "detail-close"
  );

  const status = document.getElementById(
    "detail-status"
  );

  let selectedContact = null;
  let languageConfirmed = false;

  async function api(path, options = {}) {
    const response =
      await window.urctAuth.authenticatedFetch(
        path, options
      );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }

  async function openContact(siteId, contactId) {
    panel.hidden = false;
    status.textContent = "Loading...";

    try {
      const path =
        `/sites/${encodeURIComponent(siteId)}` +
        `/contacts/${encodeURIComponent(contactId)}`;

      const contact = await api(path);

      selectedContact = { siteId, contactId };


      await chrome.storage.session.set({
        urct_selected_contact: {
          site_id: siteId,
          contact_id: contactId,
          display_name: contact.display_name
        }
      });


      title.textContent =
        `${contact.display_name} · ${siteId}`;

      const settings = contact.settings;

      language.value = settings.recipient_language;
      mode.value = settings.mode;
      style.value = settings.translation_style;
      autoDetect.checked = settings.auto_detect;
      languageConfirmed = settings.language_confirmed;

      status.textContent = "Settings loaded.";

      await window.urctHistory.openHistory(siteId, contactId, contact.display_name);

    } catch (error) {
      selectedContact = null;
      status.textContent = error.message;
    }
  }

  saveButton.addEventListener("click", async () => {
    if (!selectedContact) return;

    saveButton.disabled = true;
    status.textContent = "Saving...";

    try {
      const { siteId, contactId } = selectedContact;

      const path =
        `/sites/${encodeURIComponent(siteId)}` +
        `/contacts/${encodeURIComponent(contactId)}`;

      await api(path, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          recipient_language: language.value,
          language_confirmed: languageConfirmed,
          mode: mode.value,
          translation_style: style.value,
          auto_detect: autoDetect.checked
        })
      });

      status.textContent = "Settings saved.";

      window.dispatchEvent(
        new Event("urct:contacts-updated")
      );

    } catch (error) {
      status.textContent = error.message;

    } finally {
      saveButton.disabled = false;
    }
  });

  function closeDetails() {
    panel.hidden = true;
    selectedContact = null;
    title.textContent = "";
    status.textContent = "";
    window.urctHistory.closeHistory();
  }

  closeButton.addEventListener(
    "click",
    closeDetails
  );

  window.addEventListener(
    "urct:logout",
    closeDetails
  );

  window.urctContactDetails = {
    openContact,
    closeDetails
  };
})();
