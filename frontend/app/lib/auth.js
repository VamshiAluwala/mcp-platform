export const ACCESS_TOKEN_COOKIE_NAME = "mcp_access_token";

export function encodeOAuthState(provider, next = "") {
  if (!provider) return "";
  try {
    return window.btoa(JSON.stringify({ provider, next }));
  } catch {
    return provider;
  }
}

export function decodeOAuthState(rawState) {
  if (!rawState) {
    return { provider: "keycloak", next: "/" };
  }

  try {
    const decoded = JSON.parse(window.atob(rawState));
    return {
      ...decoded,
      provider: decoded?.provider || "keycloak",
      next: decoded?.next || "/",
    };
  } catch {
    return {
      provider: rawState,
      next: "/",
    };
  }
}

export function storeAuthSession(payload) {
  if (!payload?.access_token) return;

  window.localStorage.setItem("mcp_access_token", payload.access_token);
  if (payload.refresh_token) {
    window.localStorage.setItem("mcp_refresh_token", payload.refresh_token);
  }
  if (payload.user) {
    window.localStorage.setItem("mcp_user", JSON.stringify(payload.user));
  }

  const maxAge = Number(payload.expires_in || 3600);
  document.cookie =
    `${ACCESS_TOKEN_COOKIE_NAME}=${encodeURIComponent(payload.access_token)}; ` +
    `path=/; max-age=${maxAge}; samesite=lax`;
}

export function clearStoredAuth() {
  window.localStorage.removeItem("mcp_access_token");
  window.localStorage.removeItem("mcp_refresh_token");
  window.localStorage.removeItem("mcp_user");
  document.cookie = `${ACCESS_TOKEN_COOKIE_NAME}=; path=/; max-age=0; samesite=lax`;
}

export function redirectToNext(next, router) {
  const destination = next || "/";
  if (/^https?:\/\//i.test(destination)) {
    window.location.href = destination;
    return;
  }
  router.replace(destination);
}
