document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector("[data-toggle-password]");
  if (toggle) toggle.addEventListener("click", () => {
    const input = document.getElementById(toggle.dataset.togglePassword);
    if (!input) return;
    input.type = input.type === "password" ? "text" : "password";
    toggle.textContent = input.type === "password" ? "Show" : "Hide";
  });
  const editor = document.getElementById("codeEditor");
  const lineNumbers = document.getElementById("lineNumbers");
  if (editor && lineNumbers) {
    const updateLines = () => {
      const count = editor.value.split("\n").length;
      lineNumbers.textContent = Array.from({length: count}, (_, i) => i + 1).join("\n");
    };
    editor.addEventListener("input", updateLines);
    editor.addEventListener("scroll", () => { lineNumbers.scrollTop = editor.scrollTop; });
    updateLines();
  }
  document.querySelectorAll("[data-copy-target]").forEach(button => button.addEventListener("click", async () => {
    const el = document.getElementById(button.dataset.copyTarget);
    if (!el) return;
    try { await navigator.clipboard.writeText(el.value); button.textContent = "Copied!"; }
    catch { button.textContent = "Copy unavailable"; }
    setTimeout(() => button.textContent = "Copy code", 1500);
  }));
});
