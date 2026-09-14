import { ArcElement, Chart, DoughnutController, Tooltip } from "chart.js";

import { setPressed } from "./controls.mjs";
import { themeColor, themeRadius } from "./theme.mjs";

export const sortTooltipSubscriptions = (subscriptions, valueKey) =>
  subscriptions.toSorted((a, b) => Number(b[valueKey]) - Number(a[valueKey]));

export const initializeChart = (data) => {
  const canvas = document.getElementById("category-chart");
  const periodButtons = document.querySelectorAll("[data-chart-period]");
  const valueElements = document.querySelectorAll("[data-category-spending-value]");
  if (!(canvas instanceof HTMLCanvasElement) || !data.length) return;

  Chart.register(DoughnutController, ArcElement, Tooltip);
  const categoryTokens = {
    Essential: "--category-essential",
    Entertainment: "--category-entertainment",
    Professional: "--category-professional",
  };
  const categoryColors = () => data.map((item) => themeColor(categoryTokens[item.category]));
  const tooltipColors = () => ({
    backgroundColor: themeColor("--color-base-100"),
    bodyColor: themeColor("--color-base-content"),
    borderColor: themeColor("--glass-border"),
  });
  let activePeriod = "monthly";

  const chart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: data.map((item) => item.category),
      datasets: [
        {
          data: data.map((item) => Number(item.monthlyCost)),
          backgroundColor: categoryColors(),
          borderColor: "transparent",
          hoverOffset: 5,
          spacing: 3,
          borderRadius: themeRadius(),
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "72%",
      animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? false
        : { duration: 550 },
      plugins: {
        legend: { display: false },
        tooltip: {
          displayColors: false,
          ...tooltipColors(),
          borderWidth: 1,
          padding: 16,
          cornerRadius: themeRadius(),
          callbacks: {
            title: () => [],
            label: (context) => {
              const subscriptions = data[context.dataIndex]?.subscriptions || [];
              const valueKey = `${activePeriod}Cost`;
              return sortTooltipSubscriptions(subscriptions, valueKey).map(
                (subscription) =>
                  `${subscription.service}: ${subscription[`${valueKey}Label`]}`,
              );
            },
          },
        },
      },
    },
  });

  document.addEventListener("themechange", () => {
    chart.data.datasets[0].backgroundColor = categoryColors();
    Object.assign(chart.options.plugins.tooltip, tooltipColors());
    chart.update("none");
  });
  window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", (event) => {
    chart.options.animation = event.matches ? false : { duration: 550 };
    chart.update("none");
  });

  const updatePeriod = (period) => {
    activePeriod = period === "yearly" ? "yearly" : "monthly";
    const valueKey = `${activePeriod}Cost`;
    chart.data.datasets[0].data = data.map((item) => Number(item[valueKey]));
    chart.update();
    canvas.setAttribute(
      "aria-label",
      `${activePeriod === "yearly" ? "Yearly" : "Monthly"} spending by category`,
    );
    valueElements.forEach((element) => {
      const value = element.dataset[`${valueKey}Label`];
      if (value) element.textContent = value;
    });
    periodButtons.forEach((button) => {
      setPressed(button, button.dataset.chartPeriod === activePeriod);
    });
  };

  periodButtons.forEach((button) => {
    button.addEventListener("click", () => updatePeriod(button.dataset.chartPeriod));
  });
};
