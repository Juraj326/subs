// Resolve CSS colors through the browser before passing them to canvas consumers.
// Chart.js does not parse oklch or color-mix strings itself.
export const themeColor = (token) => {
  const probe = document.createElement("span");
  probe.style.color = `var(${token})`;
  probe.hidden = true;
  document.body.append(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 1;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.fillStyle = color;
  context.fillRect(0, 0, 1, 1);
  const [red, green, blue, alpha] = context.getImageData(0, 0, 1, 1).data;
  return `rgba(${red}, ${green}, ${blue}, ${alpha / 255})`;
};

export const themeRadius = () => {
  const root = getComputedStyle(document.documentElement);
  return parseFloat(root.getPropertyValue("--radius-box")) * parseFloat(root.fontSize);
};

export const initializeTheme = () => {
  const refresh = () => {
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", themeColor("--color-base-200"));
    document.dispatchEvent(new Event("themechange"));
  };
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", refresh);
  refresh();
};
