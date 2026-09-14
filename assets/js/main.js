import "../app.css";

import { initializeChart } from "./chart.mjs";
import { initializeClipboard } from "./clipboard.mjs";
import { initializeEditor } from "./editor.mjs";
import { initializeSubscriptions } from "./subscriptions.mjs";
import { initializeTheme } from "./theme.mjs";

initializeTheme();

if (document.querySelector("[data-subscriptions-panel]")) {
  const serverJson = (id) => JSON.parse(document.getElementById(id).textContent);
  initializeEditor({
    addDefaults: serverJson("editor-defaults"),
    subscriptionData: serverJson("subscription-data"),
  });
  initializeSubscriptions();
  initializeChart(serverJson("category-chart-data"));
  initializeClipboard();
}

document.querySelectorAll("[data-dismiss-toast]").forEach((button) => {
  button.addEventListener("click", () => {
    const toast = button.closest("[data-flash-toast]");
    toast.classList.add("is-leaving");
    window.setTimeout(() => toast.remove(), 180);
  });
});
