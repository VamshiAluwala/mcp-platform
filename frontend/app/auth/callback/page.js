"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { decodeOAuthState, redirectToNext, storeAuthSession } from "../../lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

function AuthCallbackContent() {
  const router = useRouter();
  const search = useSearchParams();
  const [message, setMessage] = useState("Completing sign-in…");
  const [isError, setIsError] = useState(false);
  const onceRef = useRef(false);

  useEffect(() => {
    if (onceRef.current) return;
    onceRef.current = true;

    const oauthError = search.get("error");
    const code = search.get("code");
    const rawState = search.get("state");
    const state = decodeOAuthState(rawState);

    if (oauthError) {
      setIsError(true);
      setMessage(`Sign-in failed: ${oauthError}`);
      return;
    }

    if (!code) {
      setIsError(true);
      setMessage("Sign-in callback is missing the authorization code.");
      return;
    }

    // Determine the provider from state
    const provider =
      state.provider === "google_direct"
        ? "google_direct"
        : state.provider === "google"
          ? "google"
          : "keycloak";

    (async () => {
      try {
        if (state.flow === "mcp_client") {
          const redirectUri = `${window.location.origin}/auth/callback`;
          const bridgeResp = await fetch(`${API}/oauth/google/complete`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              code,
              state: rawState,
              redirect_uri: redirectUri,
            }),
          });
          const bridgePayload = await bridgeResp.json();
          if (!bridgeResp.ok) {
            throw new Error(bridgePayload.detail || `Sign-in failed (${bridgeResp.status})`);
          }
          if (!bridgePayload.redirect_to) {
            throw new Error("Missing MCP client redirect target");
          }

          setMessage("Sign-in successful! Returning to MCP client…");
          window.location.href = bridgePayload.redirect_to;
          return;
        }

        const redirectUri = `${window.location.origin}/auth/callback`;
        const resp = await fetch(`${API}/api/auth/callback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, redirect_uri: redirectUri, provider }),
        });
        const payload = await resp.json();
        if (!resp.ok) {
          throw new Error(payload.detail || `Sign-in failed (${resp.status})`);
        }

        storeAuthSession(payload);

        setMessage("Sign-in successful! Redirecting…");
        redirectToNext(state.next, router);
      } catch (error) {
        setIsError(true);
        setMessage(error.message);
      }
    })();
  }, [router, search]);

  return (
    <>
      <style>{`
        @import url('https://api.fontshare.com/v2/css?f[]=satoshi@300,400,500,600,700,800,900&display=swap');
        .cb-root {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          background: radial-gradient(ellipse at 20% 50%, rgba(99,102,241,0.15) 0%, transparent 60%),
                      radial-gradient(ellipse at 80% 20%, rgba(139,92,246,0.12) 0%, transparent 60%),
                      #0a0a0f;
          font-family: 'Satoshi', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        .cb-card {
          width: 100%;
          max-width: 440px;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.09);
          border-radius: 20px;
          padding: 44px 40px 40px;
          backdrop-filter: blur(20px);
          box-shadow: 0 0 0 1px rgba(255,255,255,0.04) inset,
                      0 32px 80px rgba(0,0,0,0.5);
          text-align: center;
        }
        .cb-spinner {
          width: 44px;
          height: 44px;
          border: 3px solid rgba(99,102,241,0.2);
          border-top-color: #6366f1;
          border-radius: 50%;
          animation: cb-spin 0.8s linear infinite;
          margin: 0 auto 24px;
        }
        @keyframes cb-spin { to { transform: rotate(360deg); } }
        .cb-title {
          font-size: 20px;
          font-weight: 700;
          color: #f1f5f9;
          margin-bottom: 10px;
          letter-spacing: -0.02em;
        }
        .cb-msg {
          font-size: 14px;
          color: #64748b;
          line-height: 1.6;
        }
        .cb-error .cb-title { color: #fca5a5; }
        .cb-error .cb-spinner {
          border-top-color: #ef4444;
          animation: none;
          border: 3px solid rgba(239,68,68,0.2);
        }
      `}</style>
      <main className="cb-root">
        <section className={`cb-card${isError ? " cb-error" : ""}`}>
          <div className="cb-spinner" />
          <div className="cb-title">
            {isError ? "Sign-in Error" : "Signing you in"}
          </div>
          <p className="cb-msg">{message}</p>
        </section>
      </main>
    </>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24, background: "#0a0a0f" }}>
          <section style={{ width: "100%", maxWidth: 440, textAlign: "center", color: "#64748b", fontFamily: "'Satoshi', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
            Loading…
          </section>
        </main>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  );
}
