export const setPressed = (button, selected) => {
  button.setAttribute("aria-pressed", String(selected));
  button.classList.toggle("btn-primary", selected);
  button.classList.toggle("btn-ghost", !selected);
};
