const gallery = document.querySelector("#gallery");
const search = document.querySelector("#search");
const resultCount = document.querySelector("#result-count");
const emptyState = document.querySelector("#empty-state");
const favoritesToggle = document.querySelector("#favorites-toggle");
const favoritesKey = "ohmyzsh-gallery-favorites";
let themes = [];
let mode = "home";
let favoritesOnly = false;
const favorites = loadFavourites();

function loadFavourites() {
  try {
    const saved = JSON.parse(localStorage.getItem(favoritesKey) || "[]");
    return new Set(Array.isArray(saved) ? saved.filter((name) => typeof name === "string") : []);
  } catch {
    return new Set();
  }
}

function escapeText(value) {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function promptPreview(theme) {
  const prompt = theme.previews[mode]?.prompt || "";
  const right = theme.previews[mode]?.right || "";
  const code = mode === "home" ? "ls" : "git status";
  if (!prompt) return '<span class="terminal-line">Preview unavailable</span>';
  return `<span class="terminal-line">${prompt}${code}${right ? `<span class="right-prompt">${right}</span>` : ""}</span>`;
}

function render() {
  const query = search.value.trim().toLocaleLowerCase();
  const visible = themes.filter((theme) =>
    theme.name.toLocaleLowerCase().includes(query) &&
    (!favoritesOnly || favorites.has(theme.name))
  );
  resultCount.textContent = `${visible.length} / ${themes.length} themes`;
  emptyState.hidden = visible.length > 0;
  gallery.innerHTML = visible.map((theme) => `
    <article class="theme-card" data-name="${escapeText(theme.name)}" data-favorite="${favorites.has(theme.name)}">
      <div class="card-heading">
        <span class="theme-name">${escapeText(theme.name)}</span>
        <div class="card-actions">
          <button class="favorite-button" type="button" aria-label="Favourite ${escapeText(theme.name)}" aria-pressed="${favorites.has(theme.name)}">${favorites.has(theme.name) ? "★" : "☆"}</button>
          <button class="copy-button" type="button" title="Copy the ZSH_THEME setting for your .zshrc">Copy setting</button>
        </div>
      </div>
      <div class="terminal"><pre>${promptPreview(theme)}</pre></div>
    </article>
  `).join("");
}

search.addEventListener("input", render);

const modeButtons = document.querySelectorAll(".mode-button");
modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    mode = button.dataset.mode;
    modeButtons.forEach((item) => item.classList.toggle("active", item === button));
    render();
  });
});

favoritesToggle.addEventListener("click", () => {
  favoritesOnly = !favoritesOnly;
  favoritesToggle.setAttribute("aria-pressed", String(favoritesOnly));
  render();
});

gallery.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const name = button.closest(".theme-card").dataset.name;
  if (button.classList.contains("favorite-button")) {
    if (favorites.has(name)) favorites.delete(name);
    else favorites.add(name);
    render();
    try {
      localStorage.setItem(favoritesKey, JSON.stringify([...favorites]));
    } catch {
      resultCount.textContent = "Favourites will only be saved for this visit.";
    }
  } else if (button.classList.contains("copy-button")) {
    try {
      await navigator.clipboard.writeText(`ZSH_THEME="${name}"`);
      button.textContent = "Copied";
    } catch {
      button.textContent = "Copy failed";
    }
    setTimeout(() => { button.textContent = "Copy setting"; }, 1200);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
    event.preventDefault();
    search.focus();
  }
  if (event.key === "Escape" && document.activeElement === search) {
    search.value = "";
    search.blur();
    render();
  }
});

fetch("./themes.json")
  .then((response) => {
    if (!response.ok) throw new Error(`Could not load themes.json (${response.status})`);
    return response.json();
  })
  .then((data) => {
    themes = data;
    render();
  })
  .catch((error) => {
    resultCount.textContent = error.message;
    emptyState.hidden = false;
    emptyState.textContent = "No preview data. Run: python3 generate_previews.py";
  });
