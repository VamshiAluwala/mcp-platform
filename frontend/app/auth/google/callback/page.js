"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { decodeOAuthState, redirectToNext, storeAuthSession } from "../../../lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

function GoogleCallbackContent() {
    const router = useRouter();
    const search = useSearchParams();
    const [message, setMessage] = useState("Completing Google sign-in…");
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
            setMessage(`Google sign-in failed: ${oauthError}`);
            return;
        }

        if (!code) {
            setIsError(true);
            setMessage("Google callback is missing the authorization code.");
            return;
        }

        (async () => {
            try {
                if (state.flow === "mcp_client") {
                    const bridgeResp = await fetch(`${API}/oauth/google/complete`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            code,
                            state: rawState,
                            redirect_uri: `${window.location.origin}/auth/google/callback`,
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

                // This route is ONLY used by Google direct — always send google_direct as provider
                const redirectUri = `${window.location.origin}/auth/google/callback`;
                const resp = await fetch(`${API}/api/auth/callback`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        code,
                        redirect_uri: redirectUri,
                        provider: "google_direct",
                    }),
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
        .cb-icon {
          width: 52px;
          height: 52px;
          margin: 0 auto 20px;
        }
        .cb-spinner {
          width: 44px;
          height: 44px;
          border: 3px solid rgba(66,133,244,0.2);
          border-top-color: #4285f4;
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
          border-color: rgba(239,68,68,0.3);
        }
      `}</style>
            <main className="cb-root">
                <section className={`cb-card${isError ? " cb-error" : ""}`}>
                    {!isError && (
                        /* Official Google G icon */
                        <svg className="cb-icon" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                            <g fill="none" fillRule="evenodd">
                                <path d="M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4814h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2582h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.615z" fill="#4285F4" />
                                <path d="M9 18c2.43 0 4.4673-.806 5.9564-2.1818l-2.9087-2.2582c-.8059.54-1.8368.859-3.0477.859-2.344 0-4.3282-1.5836-5.036-3.7104H.9574v2.3318C2.4382 15.9832 5.4818 18 9 18z" fill="#34A853" />
                                <path d="M3.964 10.71c-.18-.54-.2727-1.1168-.2727-1.71s.0927-1.17.2727-1.71V4.9582H.9573C.3477 6.1731 0 7.5477 0 9s.3477 2.8268.9573 4.0418L3.964 10.71z" fill="#FBBC05" />
                                <path d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.346l2.5813-2.5814C13.4627.8918 11.4255 0 9 0 5.4818 0 2.4382 2.0168.9573 4.9582L3.964 7.29C4.6718 5.1632 6.656 3.5795 9 3.5795z" fill="#EA4335" />
                            </g>
                        </svg>
                    )}
                    <div className="cb-spinner" />
                    <div className="cb-title">
                        {isError ? "Sign-in Error" : "Signing in with Google"}
                    </div>
                    <p className="cb-msg">{message}</p>
                </section>
            </main>
        </>
    );
}

export default function GoogleCallbackPage() {
    return (
        <Suspense
            fallback={
                <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#0a0a0f" }}>
                    <section style={{ color: "#64748b", fontFamily: "'Satoshi', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>Loading…</section>
                </main>
            }
        >
            <GoogleCallbackContent />
        </Suspense>
    );
}
