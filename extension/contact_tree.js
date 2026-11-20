
(() => {
  "use strict";
    const treeContainer = document.getElementById("site-tree");
    const treeStatus = document.getElementById("tree-status");

    const siteSelect = document.getElementById("contact-site");
    const nameInput = document.getElementById("contact-name");

    const contactStatus = document.getElementById("contact-status");

    const refreshButton = document.getElementById("refresh-tree");
    const addButton = document.getElementById("add-contact");

    const expandedSites = new Set();

    async function readApi(path, options = {}) {
    const response = await window.urctAuth.authenticatedFetch(path, options);

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }

    return response.json();
    }

    function createElement(tag, text, className) {
    const element = document.createElement(tag);

    if (text !== undefined) {
        element.textContent = text;
    }

    if (className) {
        element.className = className;
    }

    return element;
    }

    async function loadContactTree() {
    treeStatus.textContent = "Loading contacts...";

    try {
        const sites = await readApi("/sites/tree");

        treeContainer.replaceChildren();
        siteSelect.replaceChildren();

        for (const site of sites) {
        const siteBox = createElement(
            "div", undefined, "site-node"
        );

        const siteTitle = createElement(
            "div",
            `📁 ${site.site_name} (${site.contacts.length})`,
            "site-title"
        );

        siteBox.appendChild(siteTitle);

        const contactList = createElement("div");

        if (!expandedSites.has(site.site_id)) {
            contactList.hidden = true;
        }

        siteTitle.addEventListener("click", () => {
            contactList.hidden = !contactList.hidden;

            if (contactList.hidden) {
            expandedSites.delete(site.site_id);
            } else {
            expandedSites.add(site.site_id);
            }
        });

        for (const contact of site.contacts) {
            const item = createElement(
            "div", undefined, "contact-item"
            );

            const info = createElement(
            "div",
            `${contact.display_name} · ${contact.recipient_language} · ${contact.mode}`,
            "contact-info"
            );

            info.style.cursor = "pointer";
            info.title = "Open contact details";

            info.addEventListener("click", () => {
            window.urctContactDetails.openContact(
                site.site_id,
                contact.id
            );
            });

            const deleteButton = createElement(
            "button", "Delete"
            );

            deleteButton.addEventListener("click", async () => {
            const confirmed = confirm(
                `Delete ${contact.display_name} from URCT contacts?`
            );

            if (!confirmed) return;

            try {
                await readApi(
                `/sites/${encodeURIComponent(site.site_id)}` +
                `/contacts/${encodeURIComponent(contact.id)}`,
                { method: "DELETE" }
                );

                contactStatus.textContent = "Contact deleted.";
                await loadContactTree();
            } catch (error) {
                contactStatus.textContent = error.message;
            }
            });

            item.append(info, deleteButton);
            contactList.appendChild(item);
        }

        siteBox.appendChild(contactList);
        treeContainer.appendChild(siteBox);

        if (site.enabled) {
            const option = document.createElement("option");
            option.value = site.site_id;
            option.textContent = site.site_name;
            siteSelect.appendChild(option);
        }
        }

        treeStatus.textContent = "Contact tree loaded.";

    } catch (error) {
        treeStatus.textContent = error.message;
    }
    }

    addButton.addEventListener("click", async () => {
    const displayName = nameInput.value.trim();
    const siteId = siteSelect.value;

    if (!displayName || !siteId) {
        contactStatus.textContent =
        "Select a site and enter a contact name.";
        return;
    }

    addButton.disabled = true;

    try {
        await readApi(
        `/sites/${encodeURIComponent(siteId)}/contacts`,
        {
            method: "POST",
            headers: {
            "Content-Type": "application/json"
            },
            body: JSON.stringify({
            display_name: displayName,
            recipient_language: "en",
            mode: "auto"
            })
        }
        );

        nameInput.value = "";
        expandedSites.add(siteId);

        contactStatus.textContent = "Contact added.";
        await loadContactTree();

    } catch (error) {
        contactStatus.textContent = error.message;
    } finally {
        addButton.disabled = false;
    }
    });

    refreshButton.addEventListener("click", loadContactTree);

    window.addEventListener("urct:login", loadContactTree);

    window.addEventListener("urct:logout", () => {
        treeContainer.replaceChildren();
        siteSelect.replaceChildren();
        treeStatus.textContent = "";
        contactStatus.textContent = "";
    });

    window.addEventListener(
        "urct:contacts-updated",
        loadContactTree
    );
})();