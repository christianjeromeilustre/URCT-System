
(() => {
  "use strict";

  const toggle = document.getElementById(
    "history-auto-save"
  );

  const status = document.getElementById(
    "history-auto-save-status"
  );

  const refreshButton = document.getElementById(
    "history-settings-refresh"
  );

  if (!toggle || !status || !refreshButton) {
    console.error("URCT History Settings HTML missing");
    return;
  }

  let loading = false;

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

  async function loadSettings() {
    if (loading) return;

    loading = true;
    toggle.disabled = true;
    refreshButton.disabled = true;
    status.textContent = "Loading settings...";

    try {
      const data = await api("/history-settings");

      toggle.checked = data.auto_save === true;
      toggle.disabled = false;

      status.textContent = toggle.checked
        ? "Auto Save is ON"
        : "Auto Save is OFF";

    } catch (error) {
      status.textContent =
        `Could not load settings: ${error.message}`;

    } finally {
      loading = false;
      refreshButton.disabled = false;
    }
  }

  toggle.addEventListener("change", async () => {
    const requested = toggle.checked;

    toggle.disabled = true;
    status.textContent = "Saving settings...";

    try {
      const data = await api("/history-settings", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          auto_save: requested
        })
      });

      toggle.checked = data.auto_save === true;

      status.textContent = toggle.checked
        ? "Auto Save is ON"
        : "Auto Save is OFF";

    } catch (error) {
      status.textContent =
        `Could not save: ${error.message}`;

      await loadSettings();
      return;

    } finally {
      if (!loading) {
        toggle.disabled = false;
      }
    }
  });

  refreshButton.addEventListener(
    "click",
    loadSettings
  );

  window.addEventListener(
    "urct:login",
    loadSettings
  );

  window.addEventListener("urct:logout", () => {
    toggle.checked = false;
    toggle.disabled = true;
    status.textContent = "Login required.";
  });

  // The login event may have occurred before
  // this script finished loading.
  loadSettings();
})();
