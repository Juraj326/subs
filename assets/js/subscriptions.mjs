import { setPressed } from "./controls.mjs";

const sortDataKey = {
  service: "sortService",
  next: "sortNext",
  charge: "sortCharge",
  monthly: "sortMonthly",
  yearly: "sortYearly",
};

const compare = (left, right, key, direction) => {
  const leftValue = left.dataset[sortDataKey[key]] || "";
  const rightValue = right.dataset[sortDataKey[key]] || "";
  if (key === "next") {
    if (!leftValue && !rightValue) return 0;
    if (!leftValue) return 1;
    if (!rightValue) return -1;
  }
  const result = ["charge", "monthly", "yearly"].includes(key)
    ? Number(leftValue) - Number(rightValue)
    : leftValue.localeCompare(rightValue, undefined, { sensitivity: "base" });
  return direction === "asc" ? result : -result;
};

export const initializeSubscriptions = () => {
  const tableContainer = document.querySelector("[data-sort-container]");
  const cardContainer = document.querySelector("[data-card-container]");
  if (!tableContainer || !cardContainer) return;

  const wrapper = document.querySelector("[data-table-overflow]");
  const scroller = wrapper.querySelector("[data-table-scroll]");
  const table = scroller.querySelector("table");
  const serviceHeading = table.querySelector("th");
  const leftFade = wrapper.querySelector('[data-table-fade="left"]');
  const rightFade = wrapper.querySelector('[data-table-fade="right"]');
  const mobileSort = document.querySelector("[data-mobile-sort]");
  const filterButtons = document.querySelectorAll("[data-status-filter]");
  const empty = document.querySelector("[data-filter-empty]");
  let currentKey = "next";
  let currentDirection = "asc";

  document.querySelectorAll("[data-service-avatar-image]").forEach((image) => {
    const revealFallback = () => image.remove();
    image.addEventListener("error", revealFallback, { once: true });
    if (image.complete && image.naturalWidth === 0) revealFallback();
  });

  const updateScrollState = () => {
    const remaining = scroller.scrollWidth - scroller.clientWidth - scroller.scrollLeft;
    wrapper.style.setProperty("--service-column-width", `${serviceHeading.offsetWidth}px`);
    leftFade.classList.toggle("opacity-0", scroller.scrollLeft <= 1);
    rightFade.classList.toggle("opacity-0", remaining <= 1);
    scroller.classList.toggle("overscroll-y-contain", scroller.scrollHeight > scroller.clientHeight + 1);
  };

  const resetScrollState = () => {
    scroller.scrollTop = 0;
    updateScrollState();
  };

  const updateSortControls = () => {
    document.querySelectorAll("[data-sort-heading]").forEach((heading) => {
      const active = heading.dataset.sortHeading === currentKey;
      heading.setAttribute("aria-sort", active ? (currentDirection === "asc" ? "ascending" : "descending") : "none");
      heading.querySelector(".sort-icon").textContent = active
        ? (currentDirection === "asc" ? "↑" : "↓")
        : "↕";
    });
    mobileSort.value = `${currentKey}:${currentDirection}`;
  };

  const applySort = (key, direction) => {
    currentKey = key;
    currentDirection = direction;
    const orderedIds = Array.from(tableContainer.children)
      .sort((left, right) => compare(left, right, key, direction))
      .map((item) => item.dataset.subscriptionId);
    for (const id of orderedIds) {
      tableContainer.append(tableContainer.querySelector(`[data-subscription-id="${id}"]`));
      cardContainer.append(cardContainer.querySelector(`[data-subscription-id="${id}"]`));
    }
    updateSortControls();
    resetScrollState();
  };

  const applyFilter = (status) => {
    let visible = 0;
    tableContainer.querySelectorAll("[data-subscription-status]").forEach((item) => {
      const matches = status === "all" || item.dataset.subscriptionStatus === status;
      item.classList.toggle("hidden", !matches);
      if (matches) visible += 1;
    });
    cardContainer.querySelectorAll("[data-subscription-status]").forEach((item) => {
      item.classList.toggle("hidden", status !== "all" && item.dataset.subscriptionStatus !== status);
    });
    filterButtons.forEach((button) => {
      setPressed(button, button.dataset.statusFilter === status);
    });
    empty.textContent = visible ? "" : `No ${status === "all" ? "" : `${status} `}subscriptions to show.`;
    empty.classList.toggle("hidden", visible > 0);
    resetScrollState();
  };

  document.querySelectorAll("[data-sort-key]").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.sortKey;
      const direction = key === currentKey && currentDirection === "asc" ? "desc" : "asc";
      applySort(key, direction);
    });
  });
  mobileSort.addEventListener("change", () => {
    const [key, direction] = mobileSort.value.split(":");
    applySort(key, direction);
  });
  filterButtons.forEach((button) => {
    button.addEventListener("click", () => applyFilter(button.dataset.statusFilter));
  });
  scroller.addEventListener("scroll", updateScrollState, { passive: true });
  const resizeObserver = new ResizeObserver(updateScrollState);
  resizeObserver.observe(scroller);
  resizeObserver.observe(table);
  resizeObserver.observe(serviceHeading);

  applySort("next", "asc");
  applyFilter("all");
};
