export const THEME_STORAGE_KEY = "mcp-theme";

export function resolvePreferredTheme() {
  if (typeof window === "undefined") return "dark";

  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }

  return window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

export function applyTheme(theme) {
  if (typeof document === "undefined") return theme;
  document.documentElement.dataset.theme = theme;
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  return theme;
}

export function toggleThemeValue(theme) {
  return theme === "light" ? "dark" : "light";
}
