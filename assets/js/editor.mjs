const EDITOR_PATH = /^\/subscriptions\/(\d+)$/;

const clearValidation = (form) => {
  form.querySelectorAll("[data-field-errors]").forEach((slot) => {
    slot.replaceChildren();
    slot.classList.add("hidden");
  });
  const formErrors = form.querySelector("[data-form-errors]");
  formErrors.querySelector("ul").replaceChildren();
  formErrors.classList.add("hidden");
  form.querySelectorAll("[aria-invalid]").forEach((field) => {
    field.setAttribute("aria-invalid", "false");
  });
};

export const initializeEditor = ({ subscriptionData, addDefaults }) => {
  const editor = document.getElementById("subscription-editor");
  const form = document.getElementById("subscription-form");
  const title = document.getElementById("editor-title");
  const kicker = document.getElementById("editor-kicker");
  const saveButton = document.getElementById("save-subscription");
  const statusField = document.getElementById("status-field");
  const statusInput = form.elements.namedItem("active");
  const protectedFields = form.querySelectorAll("[data-cancelled-protected]");
  const cancelledHelp = document.getElementById("cancelled-details-help");
  const endDate = document.getElementById("end-date-display");
  const destructiveSection = document.getElementById("destructive-section");
  const deleteButton = document.getElementById("request-delete");
  const deleteDialog = document.getElementById("delete-confirmation");
  const deleteForm = document.getElementById("delete-subscription-form");
  const deleteServiceName = document.getElementById("delete-service-name");
  const deleteSubmit = deleteForm.querySelector('[type="submit"]');
  let state = { mode: "closed", subscription: null };

  const clearDeletion = () => {
    if (deleteDialog.open) deleteDialog.close();
    deleteForm.removeAttribute("action");
    deleteSubmit.disabled = true;
    deleteServiceName.textContent = "";
  };

  const populate = (values) => {
    clearValidation(form);
    Object.entries(values).forEach(([name, value]) => {
      const field = form.elements.namedItem(name);
      if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement) {
        field.value = String(value ?? "");
      }
    });
  };

  const focusEditor = () => {
    window.setTimeout(() => {
      const target = form.querySelector('[aria-invalid="true"]:not(:disabled)') || form.elements.namedItem("service");
      if (target instanceof HTMLElement) target.focus();
    }, 0);
  };

  const syncStatus = () => {
    const locked = state.mode === "edit" && statusInput.value === "false";
    protectedFields.forEach((field) => { field.disabled = locked; });
    cancelledHelp.classList.toggle("hidden", !locked);
    endDate.value = locked ? state.subscription?.endDate || "" : "";
  };

  const stateFromLocation = () => {
    const match = EDITOR_PATH.exec(window.location.pathname);
    const subscription = match ? subscriptionData[match[1]] : null;
    if (subscription) return { mode: "edit", subscription };
    if (window.history.state?.editor === "add") return { mode: "add", subscription: null };
    return { mode: "closed", subscription: null };
  };

  const render = (nextState, { populateFields = true } = {}) => {
    const selectionChanged =
      state.mode !== nextState.mode || state.subscription?.id !== nextState.subscription?.id;
    if (selectionChanged || nextState.mode === "closed") clearDeletion();
    state = nextState;

    if (state.mode === "closed") {
      if (editor.open) editor.close();
      return;
    }

    const subscription = state.subscription;
    if (populateFields) populate(subscription?.values || addDefaults);
    form.action = subscription?.updateUrl || form.dataset.addUrl;
    editor.dataset.editorMode = state.mode;
    title.textContent = subscription?.values.service || "Add subscription";
    kicker.textContent = subscription ? "Edit subscription" : "New subscription";
    saveButton.textContent = subscription ? "Save changes" : "Add subscription";
    statusField.classList.toggle("hidden", !subscription);
    statusInput.disabled = !subscription;
    syncStatus();
    destructiveSection.classList.toggle("hidden", !subscription);
    if (!editor.open) editor.showModal();
    focusEditor();
  };

  const openAdd = () => {
    window.history.pushState({ editor: "add" }, "", "/");
    render({ mode: "add", subscription: null });
  };

  const openEdit = (subscriptionId) => {
    const subscription = subscriptionData[String(subscriptionId)];
    if (!subscription) return;
    window.history.pushState({ editor: subscription.id }, "", subscription.editorUrl);
    render({ mode: "edit", subscription });
  };

  const closeEditor = () => {
    clearDeletion();
    if (window.history.state?.editor !== undefined) {
      window.history.back();
      return;
    }
    window.location.replace("/");
  };

  document.getElementById("add-subscription").addEventListener("click", openAdd);
  document.querySelectorAll("[data-subscription-id]").forEach((element) => {
    element.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest("a, button, input, select")) return;
      openEdit(element.dataset.subscriptionId);
    });
  });
  document.querySelectorAll("[data-editor-trigger]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      openEdit(button.dataset.editorTrigger);
    });
  });
  document.querySelectorAll("[data-close-editor]").forEach((button) => {
    button.addEventListener("click", closeEditor);
  });
  editor.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeEditor();
  });
  editor.querySelector(".modal-backdrop").addEventListener("submit", (event) => {
    event.preventDefault();
    closeEditor();
  });
  editor.addEventListener("close", () => {
    state = { mode: "closed", subscription: null };
    clearDeletion();
  });
  window.addEventListener("popstate", () => {
    render(stateFromLocation());
  });

  statusInput.addEventListener("change", () => {
    if (statusInput.value === "false" && state.subscription?.values.active === "false") {
      protectedFields.forEach((field) => {
        field.value = state.subscription.values[field.name];
        field.setAttribute("aria-invalid", "false");
        const errors = document.getElementById(`${field.id}-errors`);
        errors.replaceChildren();
        errors.classList.add("hidden");
      });
    }
    syncStatus();
  });

  form.addEventListener("formdata", (event) => {
    if (statusInput.value !== "false" || state.subscription?.values.active !== "true") return;
    protectedFields.forEach((field) => { event.formData.set(field.name, field.value); });
  });

  deleteButton.addEventListener("click", () => {
    if (!state.subscription) return;
    deleteForm.action = state.subscription.removeUrl;
    deleteServiceName.textContent = state.subscription.values.service;
    deleteSubmit.disabled = false;
    deleteDialog.showModal();
  });
  deleteDialog.addEventListener("close", clearDeletion);
  deleteForm.addEventListener("submit", (event) => {
    if (!state.subscription || !deleteDialog.open || deleteSubmit.disabled) event.preventDefault();
  });
  document.querySelector("[data-cancel-delete]").addEventListener("click", () => deleteDialog.close());

  clearDeletion();
  if (editor.dataset.autoOpen === "true") {
    const subscription = subscriptionData[editor.dataset.editorSubscriptionId] || null;
    if (editor.open) editor.removeAttribute("open");
    render({ mode: subscription ? "edit" : "add", subscription }, { populateFields: false });
  } else {
    const initialState = stateFromLocation();
    if (initialState.mode === "closed") window.history.replaceState({}, "");
    render(initialState);
  }
};
