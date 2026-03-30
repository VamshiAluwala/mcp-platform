"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { encodeOAuthState, redirectToNext } from "../lib/auth";
import { applyTheme, resolvePreferredTheme, toggleThemeValue } from "../lib/theme";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SUPPORTED_PROVIDERS = new Set(["keycloak", "google", "google_direct"]);
export const dynamic = "force-dynamic";

function LoginContent() {
  const router = useRouter();
  const search = useSearchParams();
  const [loadingProvider, setLoadingProvider] = useState("");
  const [error, setError] = useState("");
  const [theme, setTheme] = useState("dark");
  const autoStartRef = useRef(false);

  const requestedProvider = search.get("provider") || "";
  const nextTarget = search.get("next") || "/";

  useEffect(() => {
    const token = window.localStorage.getItem("mcp_access_token");
    if (token) {
      redirectToNext(nextTarget, router);
      return;
    }

    if (
      requestedProvider &&
      SUPPORTED_PROVIDERS.has(requestedProvider) &&
      !autoStartRef.current
    ) {
      autoStartRef.current = true;
      void startLogin(requestedProvider);
    }
  }, [nextTarget, requestedProvider, router]);

  useEffect(() => {
    const nextTheme = resolvePreferredTheme();
    document.documentElement.dataset.theme = nextTheme;
    setTheme(nextTheme);
  }, []);

  function handleThemeToggle() {
    const nextTheme = toggleThemeValue(theme);
    applyTheme(nextTheme);
    setTheme(nextTheme);
  }

  async function startLogin(provider) {
    try {
      setError("");
      setLoadingProvider(provider);
      const redirectUri =
        provider === "google_direct"
          ? `${window.location.origin}/auth/google/callback`
          : `${window.location.origin}/auth/callback`;
      const state = encodeOAuthState(provider, nextTarget);
      window.location.href =
        `${API}/api/auth/login?provider=${provider}` +
        `&redirect_uri=${encodeURIComponent(redirectUri)}` +
        `&state=${encodeURIComponent(state)}`;
    } catch (err) {
      setError(err.message);
      setLoadingProvider(false);
    }
  }

  const isLoading = loadingProvider !== "";

  return (
    <>
      <style>{`
        .login-root {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 32px 24px;
          background:
            radial-gradient(circle at 15% 20%, rgba(0,209,255,0.16), transparent 30%),
            radial-gradient(circle at 85% 12%, rgba(255,138,61,0.18), transparent 26%),
            linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0)),
            var(--bg);
          font-family: var(--sans);
          position: relative;
          overflow: hidden;
        }

        .login-root::before {
          content: '';
          position: absolute;
          inset: 24px;
          border: 1px solid var(--border);
          border-radius: 32px;
          pointer-events: none;
          opacity: 0.4;
        }

        .login-stage {
          width: 100%;
          max-width: 1120px;
          display: grid;
          grid-template-columns: 1.1fr 0.9fr;
          gap: 28px;
          position: relative;
          z-index: 1;
        }

        .login-brand,
        .login-card {
          position: relative;
          overflow: hidden;
          border-radius: 28px;
          border: 1px solid var(--border);
          background: linear-gradient(180deg, var(--surface), rgba(255,255,255,0.02));
          backdrop-filter: blur(18px);
          box-shadow: var(--shadow-soft);
        }

        .login-brand {
          padding: 42px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          min-height: 620px;
        }

        .login-brand::after,
        .login-card::after {
          content: '';
          position: absolute;
          inset: auto auto -80px -40px;
          width: 220px;
          height: 220px;
          background: radial-gradient(circle, rgba(255,138,61,0.22), transparent 70%);
          filter: blur(18px);
          pointer-events: none;
        }

        .login-card {
          padding: 42px 38px;
        }

        .login-badge,
        .login-card-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: rgba(255,255,255,0.08);
          border: 1px solid var(--border);
          border-radius: 100px;
          padding: 6px 12px;
          font-size: 10px;
          font-weight: 600;
          color: var(--text2);
          letter-spacing: 0.06em;
          text-transform: uppercase;
          width: fit-content;
        }

        .login-card-badge {
          margin-bottom: 18px;
        }

        .login-brand-title {
          font-size: clamp(42px, 6vw, 70px);
          line-height: 0.95;
          letter-spacing: -0.06em;
          margin: 22px 0 18px;
          color: var(--text);
          max-width: 620px;
        }

        .login-brand-title span {
          color: var(--accent);
          display: block;
        }

        .login-brand-copy {
          max-width: 560px;
          font-size: 16px;
          color: var(--text2);
          line-height: 1.8;
        }

        .login-signal-row {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
          margin-top: 30px;
        }

        .login-signal {
          padding: 16px;
          border-radius: 18px;
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--border);
        }

        .login-signal-label {
          display: block;
          font-family: var(--mono);
          font-size: 10px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--text3);
          margin-bottom: 10px;
        }

        .login-signal strong {
          display: block;
          font-size: 18px;
          color: var(--text);
          margin-bottom: 6px;
        }

        .login-signal span:last-child {
          color: var(--text2);
          font-size: 13px;
          line-height: 1.6;
        }

        .login-card-title {
          font-size: 34px;
          font-weight: 700;
          color: var(--text);
          line-height: 1.1;
          margin-bottom: 8px;
          letter-spacing: -0.04em;
        }

        .login-subtitle {
          font-size: 14px;
          color: var(--text2);
          line-height: 1.6;
          margin-bottom: 30px;
        }

        .login-divider {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 18px 0;
          color: var(--text3);
          font-size: 12px;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .login-divider::before,
        .login-divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: var(--border);
        }

        .login-btn {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          padding: 14px 20px;
          border-radius: 12px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
          border: none;
          outline: none;
          position: relative;
          overflow: hidden;
          letter-spacing: -0.01em;
        }

        .login-btn:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .login-btn-keycloak {
          background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
          color: #fff;
          box-shadow: 0 18px 38px rgba(0,0,0,0.18);
        }

        .login-btn-keycloak:not(:disabled):hover {
          transform: translateY(-1px);
          box-shadow: 0 22px 44px rgba(0,0,0,0.22);
          filter: brightness(1.04);
        }

        .login-btn-keycloak:not(:disabled):active {
          transform: translateY(0);
          box-shadow: 0 12px 26px rgba(0,0,0,0.18);
        }

        .login-btn-google {
          background: var(--surface2);
          color: var(--text);
          border: 1px solid var(--border);
        }

        .login-btn-google:not(:disabled):hover {
          background: color-mix(in srgb, var(--surface2) 90%, white);
          border-color: color-mix(in srgb, var(--accent2) 40%, var(--border));
          transform: translateY(-1px);
        }

        .login-btn-google:not(:disabled):active {
          transform: translateY(0);
        }

        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255,255,255,0.32);
          border-top-color: #fff;
          border-radius: 50%;
          animation: spin 0.65s linear infinite;
          flex-shrink: 0;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .login-error {
          margin-top: 16px;
          padding: 12px 14px;
          background: color-mix(in srgb, var(--red) 12%, transparent);
          border: 1px solid color-mix(in srgb, var(--red) 30%, transparent);
          border-radius: 14px;
          color: var(--red);
          font-size: 13px;
          line-height: 1.5;
        }

        .login-footer {
          margin-top: 24px;
          font-size: 12px;
          color: var(--text3);
          line-height: 1.7;
        }

        .login-footer a {
          color: var(--accent);
          text-decoration: none;
        }

        .login-footer a:hover {
          text-decoration: underline;
        }

        .login-theme-control {
          position: fixed;
          top: 28px;
          right: 28px;
          z-index: 3;
        }

        @media (max-width: 980px) {
          .login-stage {
            grid-template-columns: 1fr;
          }

          .login-brand {
            min-height: auto;
          }
        }

        @media (max-width: 640px) {
          .login-root {
            padding: 18px;
          }

          .login-root::before {
            inset: 10px;
            border-radius: 24px;
          }

          .login-brand,
          .login-card {
            padding: 26px 22px;
            border-radius: 22px;
          }

          .login-signal-row {
            grid-template-columns: 1fr;
          }

          .login-theme-control {
            top: 18px;
            right: 18px;
          }
        }
      `}</style>

      <main className="login-root">
        <button
          type="button"
          className="theme-toggle login-theme-control"
          onClick={handleThemeToggle}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        >
          <span className="theme-toggle-icon">{theme === "dark" ? "☀" : "☾"}</span>
          <span className="theme-toggle-label">{theme === "dark" ? "Light" : "Dark"}</span>
        </button>

        <section className="login-stage">
          <aside className="login-brand">
            <div>
              <div className="login-badge">
                <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                  <circle cx="4" cy="4" r="4" fill="var(--accent2)" />
                </svg>
                Agentorix MCP Cloud
              </div>
              <h1 className="login-brand-title">
                Build. Share.
                <span>Observe every MCP session.</span>
              </h1>
              <p className="login-brand-copy">
                A sharper control room for GitHub-backed MCP deployments with Google SSO,
                per-user access, live logs, and platform-grade audit visibility.
              </p>
            </div>

            <div className="login-signal-row">
              <div className="login-signal">
                <span className="login-signal-label">Identity</span>
                <strong>Google + Keycloak</strong>
                <span>SSO-first login flow for dashboard users and MCP consumers.</span>
              </div>
              <div className="login-signal">
                <span className="login-signal-label">Access</span>
                <strong>Email allowlists</strong>
                <span>Grant specific end users access to each deployed MCP.</span>
              </div>
              <div className="login-signal">
                <span className="login-signal-label">Observability</span>
                <strong>Sessions + audit</strong>
                <span>Track which user connected, what they called, and when.</span>
              </div>
            </div>
          </aside>

          <section className="login-card">
            <div className="login-card-badge">Secure workspace sign-in</div>
            <h2 className="login-card-title">Welcome back</h2>
            <p className="login-subtitle">
              {nextTarget !== "/"
                ? "Sign in to continue straight into your MCP endpoint."
                : "Access deployments, sessions, and admin controls from one workspace."}
            </p>

            <button
              id="btn-keycloak-login"
              className="login-btn login-btn-keycloak"
              onClick={() => startLogin("keycloak")}
              disabled={isLoading}
            >
              {loadingProvider === "keycloak" ? (
                <><div className="spinner" /> Redirecting to Keycloak…</>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                    <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                    <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                  </svg>
                  Continue with Keycloak
                </>
              )}
            </button>

            <div className="login-divider">or</div>

            <button
              id="btn-google-login"
              className="login-btn login-btn-google"
              onClick={() => startLogin("google_direct")}
              disabled={isLoading}
            >
              {loadingProvider === "google_direct" ? (
                <><div className="spinner" style={{ borderTopColor: "#4285f4" }} /> Redirecting to Google…</>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                    <g fill="none" fillRule="evenodd">
                      <path d="M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4814h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2582h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.615z" fill="#4285F4" />
                      <path d="M9 18c2.43 0 4.4673-.806 5.9564-2.1818l-2.9087-2.2582c-.8059.54-1.8368.859-3.0477.859-2.344 0-4.3282-1.5836-5.036-3.7104H.9574v2.3318C2.4382 15.9832 5.4818 18 9 18z" fill="#34A853" />
                      <path d="M3.964 10.71c-.18-.54-.2727-1.1168-.2727-1.71s.0927-1.17.2727-1.71V4.9582H.9573C.3477 6.1731 0 7.5477 0 9s.3477 2.8268.9573 4.0418L3.964 10.71z" fill="#FBBC05" />
                      <path d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.346l2.5813-2.5814C13.4627.8918 11.4255 0 9 0 5.4818 0 2.4382 2.0168.9573 4.9582L3.964 7.29C4.6718 5.1632 6.656 3.5795 9 3.5795z" fill="#EA4335" />
                    </g>
                  </svg>
                  Continue with Google
                </>
              )}
            </button>

            {error && (
              <div className="login-error" role="alert">
                {error}
              </div>
            )}

            <p className="login-footer">
              By signing in you agree to platform access policies. After login you will be
              redirected to your dashboard or the MCP endpoint you requested.
            </p>
          </section>
        </section>
      </main>
    </>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24, background: "#0a0a0f" }}>
          <section style={{ width: "100%", maxWidth: 440, textAlign: "center", color: "#64748b", fontFamily: "sans-serif" }}>
            Loading…
          </section>
        </main>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
