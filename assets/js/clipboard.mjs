export const initializeClipboard = () => {
  const button = document.getElementById("copy-calendar-link");
  const feedback = document.getElementById("copy-feedback");
  if (!(button instanceof HTMLButtonElement) || !button.dataset.calendarFeedUrl) return;
  const url = button.dataset.calendarFeedUrl;
  let feedbackTimeout;

  const fallbackCopy = () => {
    const input = document.createElement("textarea");
    input.value = url;
    input.readOnly = true;
    input.className = "fixed -left-full top-0";
    document.body.append(input);
    try {
      input.focus();
      input.select();
      return document.execCommand("copy");
    } finally {
      input.remove();
      button.focus();
    }
  };

  button.addEventListener("click", async () => {
    let copied = false;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(url);
        copied = true;
      } else {
        copied = fallbackCopy();
      }
    } catch {
      try {
        copied = fallbackCopy();
      } catch {
        copied = false;
      }
    }

    if (feedback) {
      feedback.textContent = copied
        ? "Calendar link copied."
        : "Could not copy the calendar link. Please try again.";
      feedback.classList.toggle("text-error", !copied);
      feedback.classList.toggle("text-success", copied);
      window.clearTimeout(feedbackTimeout);
      feedbackTimeout = window.setTimeout(() => { feedback.textContent = ""; }, 2500);
    }
  });
};
