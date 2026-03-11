"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

function GitHubCallbackContent() {
  const router = useRouter();
  const search = useSearchParams();
  const [message, setMessage] = useState("Completing GitHub connection...");
  const [isError, setIsError] = useState(false);
  const onceRef = useRef(false);

  useEffect(() => {
    if (onceRef.current) return;
    onceRef.current = true;

    const error = search.get("error");
    const code = search.get("code");
    const state = search.get("state");

    if (error) {
      setIsError(true);
      setMessage(`GitHub OAuth failed: ${error}`);
      return;
    }

    if (!code || !state) {
      setIsError(true);
      setMessage("GitHub callback is missing code or state.");
      return;
    }

    (async () => {
      try {
        const resp = await fetch(`${API}/api/github/oauth/callback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, state }),
        });
        const payload = await resp.json();
        if (!resp.ok) {
          throw new Error(payload.detail || `GitHub OAuth failed (${resp.status})`);
        }
        setMessage(`Connected GitHub account @${payload.github_username}. Redirecting...`);
        router.replace("/");
      } catch (oauthError) {
        setIsError(true);
        setMessage(oauthError.message);
      }
    })();
  }, [router, search]);

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
        background: "#0a0a0f",
        color: isError ? "#fca5a5" : "#cbd5e1",
      }}
    >
      <section
        style={{
          width: "100%",
          maxWidth: 460,
          padding: 32,
          borderRadius: 18,
          background: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.08)",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 10 }}>
          {isError ? "GitHub Connection Error" : "Connecting GitHub"}
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.6, color: "#94a3b8" }}>{message}</div>
      </section>
    </main>
  );
}

export default function GitHubCallbackPage() {
  return (
    <Suspense fallback={null}>
      <GitHubCallbackContent />
    </Suspense>
  );
}
