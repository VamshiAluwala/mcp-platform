"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { clearStoredAuth } from "./lib/auth";
import { applyTheme, resolvePreferredTheme, toggleThemeValue } from "./lib/theme";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TITLES = {
  dashboard: ["DASHBOARD", "/ overview"],
  deploy: ["DEPLOYMENT", "/ deploy / github + external"],
  servers: ["MCP SERVERS", "/ servers"],
  sessions: ["SESSIONS", "/ observe / sessions"],
  audit: ["AUDIT LOGS", "/ observe / audit"],
  settings: ["SETTINGS", "/ oauth + access groups"],
};

function cn(...parts) {
  return parts.filter(Boolean).join(" ");
}

export default function HomePage() {
  const router = useRouter();

  const notifTimerRef = useRef(null);
  const deployTimersRef = useRef([]);
  const logPollingRef = useRef(null);

  const [authChecked, setAuthChecked] = useState(false);
  const [authToken, setAuthToken] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [theme, setTheme] = useState("dark");

  const [currentPage, setCurrentPage] = useState("dashboard");
  const [notif, setNotif] = useState({ show: false, text: "", isError: false });

  const [githubConnections, setGithubConnections] = useState([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState("");
  const [githubConnected, setGithubConnected] = useState(false);
  const [githubUser, setGithubUser] = useState(null);

  const [repos, setRepos] = useState([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [selectedRepoFullName, setSelectedRepoFullName] = useState("");
  const [selectedRepoMeta, setSelectedRepoMeta] = useState(null);

  const [entryFiles, setEntryFiles] = useState([]);
  const [entryFileLoading, setEntryFileLoading] = useState(false);
  const [selectedEntryFile, setSelectedEntryFile] = useState("");

  const [serverName, setServerName] = useState("");
  const [serverDesc, setServerDesc] = useState("");
  const [allowedEmailsInput, setAllowedEmailsInput] = useState("");
  const [selectedDeployGroupIds, setSelectedDeployGroupIds] = useState([]);
  const [runtimePort, setRuntimePort] = useState("8000");
  const [runtimeEnvInput, setRuntimeEnvInput] = useState("");

  const [externalImportName, setExternalImportName] = useState("");
  const [externalImportDescription, setExternalImportDescription] = useState("");
  const [externalAllowedEmailsInput, setExternalAllowedEmailsInput] = useState("");
  const [externalSelectedGroupIds, setExternalSelectedGroupIds] = useState([]);
  const [externalImportJson, setExternalImportJson] = useState(
    JSON.stringify(
      {
        upstream_url: "http://host.docker.internal:9000/mcp",
        headers: {},
        timeout_seconds: 30,
      },
      null,
      2,
    ),
  );
  const [externalImporting, setExternalImporting] = useState(false);

  const [deploying, setDeploying] = useState(false);
  const [deployLogs, setDeployLogs] = useState([
    { msg: "[system] Waiting for deployment...", type: "info" },
  ]);
  const [deployResult, setDeployResult] = useState(null);

  const [deployedServers, setDeployedServers] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [adminUsers, setAdminUsers] = useState([]);
  const [accessGroups, setAccessGroups] = useState([]);
  const [groupEditor, setGroupEditor] = useState({ id: "", name: "", description: "", members: "" });
  const [expandedAccessServerId, setExpandedAccessServerId] = useState("");
  const [serverAccessDrafts, setServerAccessDrafts] = useState({});
  const [auditFilterUser, setAuditFilterUser] = useState("");
  const [stats, setStats] = useState({ sessions: 0, calls: 0, users: 0 });

  const isAdmin = (currentUser?.roles || []).includes("admin");

  const runningCount = useMemo(
    () => deployedServers.filter((server) => server.status === "running").length,
    [deployedServers],
  );

  const uniqueAuditUsers = useMemo(() => {
    const set = new Set(auditLogs.map((row) => row.user).filter(Boolean));
    return Array.from(set);
  }, [auditLogs]);

  const accessGroupNameById = useMemo(
    () => Object.fromEntries(accessGroups.map((group) => [group.id, group.name])),
    [accessGroups],
  );

  const filteredAuditLogs = useMemo(() => {
    if (!auditFilterUser) return auditLogs;
    return auditLogs.filter((row) => row.user === auditFilterUser);
  }, [auditLogs, auditFilterUser]);

  const topbar = TITLES[currentPage] || TITLES.dashboard;

  const step1Done = githubConnected && !!selectedConnectionId;
  const step2Done = !!selectedRepoFullName;
  const step3Done = !!selectedEntryFile;
  const step4Done = !!deployResult?.ready;

  const step2Active = step1Done && !step2Done;
  const step3Active = step2Done && !step3Done;
  const step4Active = step3Done && !step4Done;

  const avatarLetter = (currentUser?.name || currentUser?.email || "U")
    .trim()
    .charAt(0)
    .toUpperCase();

  function clearDeployTimers() {
    deployTimersRef.current.forEach((id) => clearTimeout(id));
    deployTimersRef.current = [];
  }

  function handleThemeToggle() {
    const nextTheme = toggleThemeValue(theme);
    applyTheme(nextTheme);
    setTheme(nextTheme);
  }

  function stopLogPolling() {
    if (logPollingRef.current) {
      clearInterval(logPollingRef.current);
      logPollingRef.current = null;
    }
  }

  function notify(text, isError = false) {
    if (notifTimerRef.current) clearTimeout(notifTimerRef.current);
    setNotif({ show: true, text, isError });
    notifTimerRef.current = setTimeout(() => {
      setNotif((prev) => ({ ...prev, show: false }));
    }, 3500);
  }

  async function logout(showMessage = false) {
    clearStoredAuth();
    setAuthToken("");
    setCurrentUser(null);
    setAdminUsers([]);
    if (showMessage) notify("Logged out");
    router.replace("/login");
  }

  async function apiRequest(path, options = {}) {
    const { method = "GET", body, silent = false } = options;

    const headers = {
      "Content-Type": "application/json",
    };

    if (authToken) {
      headers.Authorization = `Bearer ${authToken}`;
    }

    const resp = await fetch(`${API}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (resp.status === 401) {
      if (!silent) notify("Session expired. Please login again.", true);
      await logout(false);
      throw new Error("Unauthorized");
    }

    const payload = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(payload.detail || payload.message || `Request failed (${resp.status})`);
    }

    return payload;
  }

  function classifyLog(line) {
    const text = (line || "").toLowerCase();
    if (text.includes("❌") || text.includes("error") || text.includes("failed")) return "err";
    if (text.includes("⚠") || text.includes("warn")) return "warn";
    if (text.includes("✅")) return "success";
    return "info";
  }

  function parseRuntimeEnvInput(raw) {
    const env = {};
    const lines = String(raw || "").split(/\r?\n/);

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;

      const separatorIndex = trimmed.indexOf("=");
      if (separatorIndex <= 0) {
        throw new Error(`Invalid env line: ${trimmed}`);
      }

      const key = trimmed.slice(0, separatorIndex).trim();
      const value = trimmed.slice(separatorIndex + 1);
      if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
        throw new Error(`Invalid env name: ${key}`);
      }
      env[key] = value;
    }

    return env;
  }

  async function loadCurrentUser() {
    try {
      const payload = await apiRequest("/api/auth/me", { silent: true });
      setCurrentUser(payload);
      window.localStorage.setItem("mcp_user", JSON.stringify(payload));
      return payload;
    } catch (err) {
      // If the backend /me call fails (e.g. backend down, or Google token
      // couldn't be verified yet), fall back to the locally stored user.
      const userRaw = window.localStorage.getItem("mcp_user");
      if (userRaw) {
        try {
          const parsed = JSON.parse(userRaw);
          setCurrentUser(parsed);
          return parsed;
        } catch {
          return null;
        }
      } else {
        // Surface the error only if we have no fallback
        throw err;
      }
    }
  }

  async function loadAdminUsers(silent = true, adminOverride = isAdmin) {
    if (!adminOverride) {
      setAdminUsers([]);
      return [];
    }

    try {
      const payload = await apiRequest("/api/admin/users", { silent });
      const rows = (payload.users || []).map((item) => ({
        id: item.id,
        email: item.email || item.id,
        name: item.name || "—",
        tenant: item.tenant_id,
        provider: item.provider || "unknown",
        roles: item.roles || [],
        activeSessions: Number(item.active_sessions || 0),
        totalSessions: Number(item.total_sessions || 0),
        totalCalls: Number(item.total_calls || 0),
        deployedServers: Number(item.deployed_servers || 0),
        lastLogin: item.last_login_at ? new Date(item.last_login_at).toLocaleString() : "—",
        lastActivity: item.last_activity_at ? new Date(item.last_activity_at).toLocaleString() : "—",
      }));
      setAdminUsers(rows);
      return rows;
    } catch (error) {
      setAdminUsers([]);
      if (!silent) notify(`Failed to load admin users: ${error.message}`, true);
      return [];
    }
  }

  async function loadAccessGroups(silent = true) {
    try {
      const payload = await apiRequest("/api/access-groups/", { silent });
      setAccessGroups(payload.groups || []);
      return payload.groups || [];
    } catch (error) {
      setAccessGroups([]);
      if (!silent) notify(`Failed to load access groups: ${error.message}`, true);
      return [];
    }
  }

  async function loadServers(silent = true) {
    const payload = await apiRequest("/api/mcp/", { silent });
    const mapped = (payload || []).map((server) => ({
      id: server.id,
      name: server.name,
      repo: server.config?.github_repo || server.config?.import_config?.upstream_url || "manual",
      entryFile: server.config?.entry_file || "server.py",
      url: server.endpoint_url,
      status: server.status,
      description: server.description || "",
      config: server.config || {},
      sourceType: server.config?.source_type || "manual_code",
      allowedEmails: server.config?.allowed_user_emails || [],
      allowedGroupIds: server.config?.allowed_group_ids || [],
      createdAt: server.created_at || null,
    }));
    setDeployedServers(mapped);
  }

  async function loadSessions() {
    try {
      const payload = await apiRequest("/api/sessions/", { silent: true });
      const rows = (payload.sessions || []).map((session) => {
        const matchingServer = deployedServers.find((item) => item.id === session.mcp_server_id);
        return {
          id: session.id,
          email: session.user_email || currentUser?.email || "unknown",
          server: matchingServer?.name || session.mcp_server_id,
          started: session.started_at ? new Date(session.started_at).toLocaleTimeString() : "—",
          calls: Number(session.call_count || 0),
          status: session.status === "active" ? "active" : "stopped",
        };
      });
      setSessions(rows);
    } catch (error) {
      setSessions([]);
      if (deployedServers.length > 0) {
        notify(`Failed to load sessions: ${error.message}`, true);
      }
    }
  }

  async function loadAuditLogs() {
    try {
      const payload = await apiRequest("/api/audit/?limit=100", { silent: true });
      const rows = (payload.items || []).map((item) => {
        const matchingServer = deployedServers.find((server) => server.id === item.mcp_server_id);
        const durationValue = item.duration_ms ?? "";
        return {
          id: item.id,
          time: item.called_at ? new Date(item.called_at).toLocaleTimeString() : "—",
          user: item.user_email || item.user_id,
          tenant: item.tenant_id,
          tool: item.tool_name,
          server: matchingServer?.name || item.mcp_server_id,
          duration:
            durationValue === ""
              ? "—"
              : String(durationValue).includes("ms")
                ? String(durationValue)
                : `${durationValue}ms`,
          status: item.status || "success",
        };
      });
      setAuditLogs(rows);
    } catch (error) {
      setAuditLogs([]);
      if (deployedServers.length > 0) {
        notify(`Failed to load audit logs: ${error.message}`, true);
      }
    }
  }

  async function loadGitHubConnections(options = {}) {
    const { silent = false } = options;

    try {
      const payload = await apiRequest("/api/github/connections", { silent: true });
      const connections = payload.connections || [];
      setGithubConnections(connections);
      setGithubConnected(connections.length > 0);

      const defaultConnectionId =
        connections.find((item) => item.id === selectedConnectionId)?.id ||
        connections[0]?.id ||
        "";
      setSelectedConnectionId(defaultConnectionId);

      const selectedConnection =
        connections.find((item) => item.id === defaultConnectionId) || null;
      setGithubUser(
        selectedConnection
          ? {
              login: selectedConnection.github_username,
              accountUrl: selectedConnection.account_url,
              connectionName: selectedConnection.connection_name,
            }
          : null,
      );

      if (!silent && connections.length > 0) {
        notify(`Loaded ${connections.length} GitHub connection${connections.length > 1 ? "s" : ""}`);
      }

      return defaultConnectionId;
    } catch (error) {
      setGithubConnections([]);
      setSelectedConnectionId("");
      setGithubConnected(false);
      setGithubUser(null);
      if (!silent) notify(`Failed to load GitHub connections: ${error.message}`, true);
      return "";
    }
  }

  async function loadRepos(options = {}) {
    const { silent = false, connectionId = selectedConnectionId } = options;
    if (!connectionId) {
      setRepos([]);
      return false;
    }

    setReposLoading(true);

    try {
      const payload = await apiRequest(`/api/github/repos?connection_id=${encodeURIComponent(connectionId)}`, { silent: true });
      const reposData = payload.repos || [];
      setRepos(reposData);
      setGithubConnected(true);
      if (!silent) notify(`Found ${reposData.length} Python repos`);
      return true;
    } catch (error) {
      setRepos([]);
      if (!silent) notify(`Failed to load repos: ${error.message}`, true);
      return false;
    } finally {
      setReposLoading(false);
    }
  }

  async function connectGitHub() {
    try {
      const payload = await apiRequest("/api/github/oauth/url");
      window.location.href = payload.login_url;
    } catch (error) {
      notify(`GitHub OAuth failed: ${error.message}`, true);
    }
  }

  async function disconnectGitHub() {
    if (!selectedConnectionId) {
      notify("Select a GitHub connection first", true);
      return;
    }

    try {
      await apiRequest(`/api/github/disconnect/${selectedConnectionId}`, { method: "POST", silent: true });
    } catch {
      // ignore disconnect errors; clear UI state below
    }

    setRepos([]);
    setSelectedRepoFullName("");
    setSelectedRepoMeta(null);
    setEntryFiles([]);
    setSelectedEntryFile("");
    const remainingConnectionId = await loadGitHubConnections({ silent: true });
    if (remainingConnectionId) {
      await loadRepos({ silent: true, connectionId: remainingConnectionId });
    }
    notify("GitHub connection removed");
  }

  async function onRepoSelected(fullName) {
    setSelectedRepoFullName(fullName);
    setSelectedEntryFile("");
    setEntryFiles([]);

    if (!fullName) {
      setSelectedRepoMeta(null);
      return;
    }

    const repo = repos.find((item) => item.full_name === fullName);
    setSelectedRepoMeta(repo || null);

    const autoName = fullName.split("/")[1] || "";
    setServerName(autoName);

    await loadRepoFiles(fullName);
  }

  async function loadRepoFiles(fullName) {
    const [owner, repo] = fullName.split("/");
    setEntryFileLoading(true);

    try {
      const payload = await apiRequest(
        `/api/github/repos/${owner}/${repo}/files?connection_id=${encodeURIComponent(selectedConnectionId)}`,
      );
      const files = payload.python_files || [];
      const isPriority = (name) => /\b(main|server|app)\b/.test(name);
      const priority = files.filter(isPriority);
      const rest = files.filter((name) => !isPriority(name));
      const ordered = [...priority, ...rest];

      setEntryFiles(ordered);
      if (priority.length > 0) {
        setSelectedEntryFile(priority[0]);
      }
    } catch (error) {
      notify(`Failed to load files: ${error.message}`, true);
      setEntryFiles([]);
    } finally {
      setEntryFileLoading(false);
    }
  }

  async function fetchServerLogs(serverId) {
    try {
      const payload = await apiRequest(`/api/mcp/${serverId}/logs`, { silent: true });
      const rows = (payload.logs || []).map((line) => ({
        msg: line,
        type: classifyLog(line),
      }));
      setDeployLogs(rows.length ? rows : [{ msg: "[system] Waiting for deployment...", type: "info" }]);
      if (payload.status && payload.status !== "running") {
        stopLogPolling();
      }
    } catch {
      // ignore polling errors
    }
  }

  function startLogPolling(serverId) {
    stopLogPolling();
    void fetchServerLogs(serverId);
    logPollingRef.current = setInterval(() => {
      void fetchServerLogs(serverId);
    }, 2000);
  }

  async function deployMCP() {
    if (!selectedConnectionId) {
      notify("Please connect and select a GitHub account", true);
      return;
    }
    if (!selectedRepoFullName) {
      notify("Please select a repo", true);
      return;
    }
    if (!selectedEntryFile) {
      notify("Please select an entry file", true);
      return;
    }
    if (!serverName.trim()) {
      notify("Please enter a server name", true);
      return;
    }

    clearDeployTimers();
    stopLogPolling();
    setDeploying(true);
    setDeployLogs([{ msg: "[system] Starting deployment...", type: "info" }]);

    try {
      const allowedEmails = allowedEmailsInput
        .split(",")
        .map((email) => email.trim().toLowerCase())
        .filter(Boolean);
      const parsedRuntimePort = Number(runtimePort || "8000");
      const runtimeEnv = parseRuntimeEnvInput(runtimeEnvInput);

      const payload = await apiRequest("/api/github/deploy", {
        method: "POST",
        body: {
          connection_id: selectedConnectionId,
          repo_full_name: selectedRepoFullName,
          entry_file: selectedEntryFile,
          server_name: serverName.trim(),
          description: serverDesc.trim(),
          allowed_emails: allowedEmails,
          allowed_group_ids: selectedDeployGroupIds,
          runtime_port: Number.isFinite(parsedRuntimePort) ? parsedRuntimePort : 8000,
          runtime_env: runtimeEnv,
        },
      });

      setDeployResult({
        ready: true,
        serverId: payload.server_id,
        serverName: serverName.trim(),
        mcpUrl: payload.endpoint_url,
        clientConfig: payload.client_config || null,
        allowedEmails: payload.allowed_emails || allowedEmails,
        allowedGroupIds: payload.allowed_group_ids || selectedDeployGroupIds,
      });

      await loadServers();
      await loadSessions();
      await loadAuditLogs();
      startLogPolling(payload.server_id);
      notify(`✅ ${serverName.trim()} is live!`);
    } catch (error) {
      setDeployLogs([{ msg: `[error] ${error.message}`, type: "err" }]);
      notify(`Deployment failed: ${error.message}`, true);
    } finally {
      setDeploying(false);
    }
  }

  async function importExternalMCP() {
    let parsedConfig;
    try {
      parsedConfig = JSON.parse(externalImportJson);
    } catch {
      notify("External import JSON is invalid", true);
      return;
    }

    if (!externalImportName.trim()) {
      notify("Enter a name for the external MCP", true);
      return;
    }

    setExternalImporting(true);
    try {
      const allowedEmails = externalAllowedEmailsInput
        .split(",")
        .map((email) => email.trim().toLowerCase())
        .filter(Boolean);

      const payload = await apiRequest("/api/mcp/import", {
        method: "POST",
        body: {
          name: externalImportName.trim(),
          description: externalImportDescription.trim(),
          json_config: parsedConfig,
          allowed_emails: allowedEmails,
          allowed_group_ids: externalSelectedGroupIds,
        },
      });

      setDeployResult({
        ready: true,
        serverId: payload.server_id,
        serverName: externalImportName.trim(),
        mcpUrl: payload.endpoint_url,
        clientConfig: payload.client_config || null,
        allowedEmails: payload.allowed_emails || allowedEmails,
        allowedGroupIds: payload.allowed_group_ids || externalSelectedGroupIds,
      });

      await loadServers();
      await loadSessions();
      await loadAuditLogs();
      startLogPolling(payload.server_id);
      notify(`✅ ${externalImportName.trim()} is imported`);
    } catch (error) {
      notify(`External import failed: ${error.message}`, true);
    } finally {
      setExternalImporting(false);
    }
  }

  async function copyText(text, successMsg = "Copied to clipboard!") {
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      notify(successMsg);
    } catch {
      notify("Copy failed. Please copy manually.", true);
    }
  }

  function copyServerUrl(id) {
    const server = deployedServers.find((item) => item.id === id);
    if (!server) return;
    copyText(server.url, "URL copied!");
  }

  async function stopServer(id) {
    try {
      await apiRequest(`/api/mcp/${id}`, { method: "DELETE" });
      await loadServers();
      await loadSessions();
      notify("Server stopped");
    } catch (error) {
      notify(`Failed to stop server: ${error.message}`, true);
    }
  }

  function viewLogs(id) {
    const server = deployedServers.find((item) => item.id === id);
    if (!server) return;

    setCurrentPage("deploy");
    setDeployResult({
      ready: true,
      serverId: server.id,
      serverName: server.name,
      mcpUrl: server.url,
      clientConfig: server.config?.client_config || null,
      allowedEmails: server.config?.allowed_user_emails || [],
      allowedGroupIds: server.config?.allowed_group_ids || [],
    });

    startLogPolling(server.id);
    notify("Showing logs for server");
  }

  function openAccessEditor(server) {
    setExpandedAccessServerId((current) => (current === server.id ? "" : server.id));
    setServerAccessDrafts((current) => ({
      ...current,
      [server.id]: {
        emailsInput: (server.allowedEmails || []).join(", "),
        groupIds: server.allowedGroupIds || [],
        saving: false,
      },
    }));
  }

  async function saveServerAccess(serverId) {
    const draft = serverAccessDrafts[serverId];
    if (!draft) return;

    setServerAccessDrafts((current) => ({
      ...current,
      [serverId]: { ...current[serverId], saving: true },
    }));

    try {
      const payload = await apiRequest(`/api/mcp/${serverId}/access`, {
        method: "POST",
        body: {
          emails: draft.emailsInput
            .split(",")
            .map((email) => email.trim().toLowerCase())
            .filter(Boolean),
          group_ids: draft.groupIds || [],
        },
      });

      await loadServers();
      if (deployResult?.serverId === serverId) {
        setDeployResult((current) => current ? ({
          ...current,
          allowedEmails: payload.allowed_emails || [],
          allowedGroupIds: payload.allowed_group_ids || [],
          clientConfig: payload.client_config || current.clientConfig,
        }) : current);
      }
      notify("Server access updated");
    } catch (error) {
      notify(`Failed to update access: ${error.message}`, true);
    } finally {
      setServerAccessDrafts((current) => ({
        ...current,
        [serverId]: { ...current[serverId], saving: false },
      }));
    }
  }

  async function saveAccessGroup() {
    if (!groupEditor.name.trim()) {
      notify("Access group name is required", true);
      return;
    }

    const body = {
      name: groupEditor.name.trim(),
      description: groupEditor.description.trim(),
      members: groupEditor.members
        .split(",")
        .map((email) => email.trim().toLowerCase())
        .filter(Boolean),
    };

    try {
      if (groupEditor.id) {
        await apiRequest(`/api/access-groups/${groupEditor.id}`, { method: "PUT", body });
        notify("Access group updated");
      } else {
        await apiRequest("/api/access-groups/", { method: "POST", body });
        notify("Access group created");
      }
      setGroupEditor({ id: "", name: "", description: "", members: "" });
      await loadAccessGroups(false);
    } catch (error) {
      notify(`Failed to save access group: ${error.message}`, true);
    }
  }

  async function deleteAccessGroup(groupId) {
    try {
      await apiRequest(`/api/access-groups/${groupId}`, { method: "DELETE" });
      if (groupEditor.id === groupId) {
        setGroupEditor({ id: "", name: "", description: "", members: "" });
      }
      await loadAccessGroups(false);
      notify("Access group deleted");
    } catch (error) {
      notify(`Failed to delete access group: ${error.message}`, true);
    }
  }

  async function testAPI() {
    try {
      const resp = await fetch(`${API}/health`);
      if (resp.ok) notify("✅ Backend API is running!");
      else notify("⚠️ Backend responded but with error", true);
    } catch {
      notify("❌ Backend not reachable. Is docker-compose running?", true);
    }
  }

  function showPage(name) {
    setCurrentPage(name);
    if (name === "sessions") void loadSessions();
    if (name === "audit") void loadAuditLogs();
  }

  useEffect(() => {
    return () => {
      if (notifTimerRef.current) clearTimeout(notifTimerRef.current);
      clearDeployTimers();
      stopLogPolling();
    };
  }, []);

  useEffect(() => {
    const nextTheme = resolvePreferredTheme();
    document.documentElement.dataset.theme = nextTheme;
    setTheme(nextTheme);
  }, []);

  useEffect(() => {
    const token = window.localStorage.getItem("mcp_access_token");
    const userRaw = window.localStorage.getItem("mcp_user");
    if (!token) {
      router.replace("/login");
      setAuthChecked(true);
      return;
    }

    setAuthToken(token);
    if (userRaw) {
      try {
        setCurrentUser(JSON.parse(userRaw));
      } catch {
        setCurrentUser(null);
      }
    }
    setAuthChecked(true);
  }, [router]);

  useEffect(() => {
    if (!authToken) return;

    let mounted = true;
    (async () => {
      let resolvedIsAdmin = false;
      try {
        // Load user first — graceful fallback inside loadCurrentUser
        const resolvedUser = await loadCurrentUser();
        resolvedIsAdmin = (resolvedUser?.roles || []).includes("admin");
      } catch (error) {
        // Truly unrecoverable (no stored user either) — do nothing, user still sees dashboard
        if (mounted) console.warn("Failed to load user:", error.message);
      }

      // Load the rest independently so one failure doesn't block the others
      const results = await Promise.allSettled([
        loadServers(true),
        loadAuditLogs(),
        loadGitHubConnections({ silent: true }),
        loadAccessGroups(true),
        (resolvedIsAdmin ? loadAdminUsers(true, true) : Promise.resolve([])),
      ]);

      // Sessions depend on servers so load after
      await loadSessions().catch(() => { });

      const githubResult = results[2];
      if (mounted) {
        const defaultConnectionId = githubResult.status === "fulfilled" ? githubResult.value : "";
        if (defaultConnectionId) {
          await loadRepos({ silent: true, connectionId: defaultConnectionId });
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, [authToken]);

  useEffect(() => {
    if (deployedServers.length === 0 && sessions.length === 0 && auditLogs.length === 0) {
      setStats({ sessions: 0, calls: 0, users: 0 });
      return;
    }

    const uniqueUsers = new Set(auditLogs.map((row) => row.user).filter(Boolean));
    const activeSessions = sessions.filter((session) => session.status === "active").length;

    setStats({
      sessions: activeSessions,
      calls: auditLogs.length,
      users: isAdmin && adminUsers.length > 0 ? adminUsers.length : uniqueUsers.size,
    });
  }, [adminUsers, auditLogs, deployedServers, isAdmin, sessions]);

  useEffect(() => {
    if (!authToken) return;
    if (currentPage === "sessions") void loadSessions();
    if (currentPage === "audit") void loadAuditLogs();
    if (currentPage === "dashboard" && isAdmin) void loadAdminUsers(true);
  }, [currentPage, authToken, deployedServers.length, isAdmin]);

  useEffect(() => {
    if (!authToken || !selectedConnectionId) return;
    void loadRepos({ silent: true, connectionId: selectedConnectionId });
  }, [authToken, selectedConnectionId]);

  useEffect(() => {
    const selectedConnection =
      githubConnections.find((item) => item.id === selectedConnectionId) || null;
    setGithubUser(
      selectedConnection
        ? {
            login: selectedConnection.github_username,
            accountUrl: selectedConnection.account_url,
            connectionName: selectedConnection.connection_name,
          }
        : null,
    );
  }, [githubConnections, selectedConnectionId]);

  useEffect(() => {
    setSelectedRepoFullName("");
    setSelectedRepoMeta(null);
    setEntryFiles([]);
    setSelectedEntryFile("");
  }, [selectedConnectionId]);

  if (!authChecked || !authToken) {
    return null;
  }

  return (
    <>
      <div className="shell">
        <aside className="sidebar">
          <div className="logo">
            <div className="logo-icon">⚡</div>
            <div>
              <div className="logo-text">MCP CLOUD</div>
              <div className="logo-sub">v1.0 · local dev</div>
            </div>
          </div>

          <nav>
            <div className="nav-section">Overview</div>
            <div className={cn("nav-item", currentPage === "dashboard" && "active")} onClick={() => showPage("dashboard")}>
              <span className="nav-icon">◈</span> Dashboard
            </div>

            <div className="nav-section">Deploy</div>
            <div className={cn("nav-item", currentPage === "deploy" && "active")} onClick={() => showPage("deploy")}>
              <span className="nav-icon">⬡</span> GitHub Import
            </div>
            <div className={cn("nav-item", currentPage === "servers" && "active")} onClick={() => showPage("servers")}>
              <span className="nav-icon">▣</span> MCP Servers
              <span className="badge green" id="server-count">
                {runningCount}
              </span>
            </div>

            <div className="nav-section">Observe</div>
            <div className={cn("nav-item", currentPage === "sessions" && "active")} onClick={() => showPage("sessions")}>
              <span className="nav-icon">◎</span> Sessions
            </div>
            <div className={cn("nav-item", currentPage === "audit" && "active")} onClick={() => showPage("audit")}>
              <span className="nav-icon">≡</span> Audit Logs
            </div>

            <div className="nav-section">Settings</div>
            <div className={cn("nav-item", currentPage === "settings" && "active")} onClick={() => showPage("settings")}>
              <span className="nav-icon">◌</span> OAuth Config
            </div>
          </nav>
        </aside>

        <div className="main">
          <div className="topbar">
            <div className="topbar-heading">
              <span className="topbar-title" id="topbar-title">
                {topbar[0]}
              </span>
              <span className="topbar-crumb" id="topbar-crumb">
                {topbar[1]}
              </span>
            </div>
            <div className="topbar-right">
              <div className="status-dot" />
              <span style={{ fontSize: 12, color: "var(--text3)", fontFamily: "var(--mono)" }}>
                API: localhost:8000
              </span>
              <button
                type="button"
                className="theme-toggle"
                onClick={handleThemeToggle}
                aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
                title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              >
                <span className="theme-toggle-icon">{theme === "dark" ? "☀" : "☾"}</span>
                <span className="theme-toggle-label">{theme === "dark" ? "Light" : "Dark"}</span>
              </button>
              <span style={{ fontSize: 12, color: "var(--text3)", fontFamily: "var(--mono)" }}>
                {currentUser?.email || "logged user"}
              </span>
              {isAdmin && <span className="chip chip-red">ADMIN</span>}
              <div className="avatar" title="Logout" onClick={() => logout(true)}>
                {avatarLetter}
              </div>
            </div>
          </div>

          <div className="content">
            <div className={cn("page", currentPage === "dashboard" && "active")} id="page-dashboard">
              <div className="section-header">
                <div>
                  <div className="section-title">Platform Overview</div>
                  <div className="section-sub">Your MCP hosting control center</div>
                </div>
                <button className="btn btn-primary" onClick={() => showPage("deploy")}>
                  ⬡ Deploy New MCP
                </button>
              </div>

              <div className="overview-hero">
                <div className="overview-copy">
                  <div className="hero-eyebrow">
                    {isAdmin ? "ADMIN CONTROL ROOM" : "DEPLOYMENT STUDIO"}
                  </div>
                  <h2 className="hero-title">
                    Secure MCP deployment with Google SSO, share controls, and live observability.
                  </h2>
                  <p className="hero-text">
                    Launch GitHub-backed MCP servers, approve which users can open them, and watch
                    sessions, audit activity, and deploy health from one workspace.
                  </p>
                  <div className="hero-actions">
                    <button className="btn btn-primary" onClick={() => showPage("deploy")}>
                      ⬡ New Deploy
                    </button>
                    <button className="btn btn-secondary" onClick={() => showPage("sessions")}>
                      ◎ Live Sessions
                    </button>
                  </div>
                </div>

                <div className="overview-signal-grid">
                  <div className="signal-tile">
                    <span className="signal-kicker">Theme</span>
                    <strong>{theme === "dark" ? "Night Shift" : "Studio Light"}</strong>
                    <span className="signal-meta">One-click visual mode across dashboard and login</span>
                  </div>
                  <div className="signal-tile">
                    <span className="signal-kicker">Access</span>
                    <strong>{allowedEmailsInput ? "Shared rollout" : "Owner-only draft"}</strong>
                    <span className="signal-meta">Allowlisted users sign in with Google before MCP access</span>
                  </div>
                  <div className="signal-tile">
                    <span className="signal-kicker">Visibility</span>
                    <strong>{auditLogs.length} recent events</strong>
                    <span className="signal-meta">Every tool call and session is tracked per user</span>
                  </div>
                </div>
              </div>

              <div className="stats-row">
                <div className="stat-card purple">
                  <div className="stat-label">MCP Servers</div>
                  <div className="stat-value" id="stat-servers">
                    {deployedServers.length}
                  </div>
                  <div className="stat-sub">deployed</div>
                </div>
                <div className="stat-card cyan">
                  <div className="stat-label">Active Sessions</div>
                  <div className="stat-value" id="stat-sessions">
                    {stats.sessions}
                  </div>
                  <div className="stat-sub">right now</div>
                </div>
                <div className="stat-card green">
                  <div className="stat-label">Tool Calls</div>
                  <div className="stat-value" id="stat-calls">
                    {stats.calls}
                  </div>
                  <div className="stat-sub">total logged</div>
                </div>
                <div className="stat-card red">
                  <div className="stat-label">Identities</div>
                  <div className="stat-value" id="stat-users">
                    {stats.users}
                  </div>
                  <div className="stat-sub">tracked users</div>
                </div>
              </div>

              <div className="grid-2">
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">Recent Servers</div>
                    <button className="btn btn-secondary btn-sm" onClick={() => showPage("servers")}>
                      View all
                    </button>
                  </div>

                  <div id="dash-servers-list">
                    {deployedServers.length === 0 ? (
                      <div className="empty">
                        <div className="empty-icon">⬡</div>
                        <div className="empty-title">No servers yet</div>
                        <div className="empty-sub">Import from GitHub to deploy your first MCP</div>
                      </div>
                    ) : (
                      deployedServers
                        .slice(-3)
                        .reverse()
                        .map((server) => (
                          <div
                            key={server.id}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 12,
                              padding: "10px 0",
                              borderBottom: "1px solid var(--border)",
                            }}
                          >
                            <div className="mcp-icon" style={{ width: 30, height: 30, fontSize: 14 }}>
                              ⬡
                            </div>
                            <div>
                              <div style={{ fontSize: 13, fontWeight: 500 }}>{server.name}</div>
                              <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "var(--mono)" }}>
                                {server.repo}
                              </div>
                            </div>
                            <span className={cn("chip", server.status === "running" ? "chip-green" : "chip-red")} style={{ marginLeft: "auto" }}>
                              {server.status === "running" ? "● LIVE" : "○ STOPPED"}
                            </span>
                          </div>
                        ))
                    )}
                  </div>
                </div>

                <div className="card">
                  <div className="card-header">
                    <div className="card-title">Recent Audit Events</div>
                    <button className="btn btn-secondary btn-sm" onClick={() => showPage("audit")}>
                      View all
                    </button>
                  </div>

                  <div id="dash-audit-list">
                    {auditLogs.length === 0 ? (
                      <div className="empty">
                        <div className="empty-icon">≡</div>
                        <div className="empty-title">No events yet</div>
                        <div className="empty-sub">Tool calls will appear here in real-time</div>
                      </div>
                    ) : (
                      auditLogs.slice(0, 4).map((log) => (
                        <div
                          key={log.id}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 10,
                            padding: "10px 0",
                            borderBottom: "1px solid var(--border)",
                          }}
                        >
                          <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "var(--mono)" }}>{log.time}</div>
                          <code
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 11,
                              color: "var(--accent2)",
                              background: "rgba(0,229,192,0.08)",
                              padding: "2px 6px",
                              borderRadius: 4,
                            }}
                          >
                            {log.tool}
                          </code>
                          <span className={cn("chip", log.status === "success" ? "chip-green" : "chip-red")} style={{ marginLeft: "auto" }}>
                            {log.status}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {isAdmin && (
                <div className="card" style={{ marginTop: 20 }}>
                  <div className="card-header">
                    <div>
                      <div className="card-title">Platform Users</div>
                      <div className="section-sub">Global admin view of sign-ins, sessions, deploys, and usage</div>
                    </div>
                    <button className="btn btn-secondary btn-sm" onClick={() => loadAdminUsers(false)}>
                      ↻ Refresh
                    </button>
                  </div>

                  <table>
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Provider</th>
                        <th>Roles</th>
                        <th>Active Sessions</th>
                        <th>Total Calls</th>
                        <th>Deploys</th>
                        <th>Last Login</th>
                      </tr>
                    </thead>
                    <tbody>
                      {adminUsers.length === 0 ? (
                        <tr>
                          <td colSpan={7} style={{ textAlign: "center", color: "var(--text3)", padding: 40 }}>
                            No platform users loaded yet
                          </td>
                        </tr>
                      ) : (
                        adminUsers.map((user) => (
                          <tr key={user.id}>
                            <td>
                              <div style={{ display: "grid", gap: 4 }}>
                                <span>{user.email}</span>
                                <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "var(--mono)" }}>
                                  {user.tenant}
                                </span>
                              </div>
                            </td>
                            <td>{user.provider}</td>
                            <td style={{ fontSize: 12 }}>{user.roles.join(", ") || "user"}</td>
                            <td style={{ fontFamily: "var(--mono)" }}>{user.activeSessions}</td>
                            <td style={{ fontFamily: "var(--mono)" }}>{user.totalCalls}</td>
                            <td style={{ fontFamily: "var(--mono)" }}>{user.deployedServers}</td>
                            <td style={{ fontSize: 12, color: "var(--text3)" }}>{user.lastLogin}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className={cn("page", currentPage === "deploy" && "active")} id="page-deploy">
              <div className="section-header">
                <div>
                  <div className="section-title">Deployment Control Room</div>
                  <div className="section-sub">GitHub deploys and external MCP imports share the same auth, access, and audit gateway</div>
                </div>
              </div>

              <div className="steps" style={{ marginBottom: 28 }}>
                <div className={cn("step", step1Done ? "done" : "active")} id="step-1">
                  <div className="step-num">{step1Done ? "✓" : "1"}</div>
                  Connect GitHub
                </div>
                <div className="step-arrow" />
                <div className={cn("step", step2Done ? "done" : step2Active ? "active" : "")} id="step-2">
                  <div className="step-num">{step2Done ? "✓" : "2"}</div>
                  Select Repo
                </div>
                <div className="step-arrow" />
                <div className={cn("step", step3Done ? "done" : step3Active ? "active" : "")} id="step-3">
                  <div className="step-num">{step3Done ? "✓" : "3"}</div>
                  Pick Entry File
                </div>
                <div className="step-arrow" />
                <div className={cn("step", step4Done ? "done" : step4Active ? "active" : "")} id="step-4">
                  <div className="step-num">{step4Done ? "✓" : "4"}</div>
                  Deploy &amp; Run
                </div>
              </div>

              <div className="card" style={{ marginBottom: 20 }} id="github-connect-card">
                <div className="card-header">
                  <div className="card-title">① GitHub Connection</div>
                  <div id="github-status-badge" />
                </div>

                {!githubConnected ? (
                  <div id="github-connect-form">
                    <p style={{ fontSize: 13, color: "var(--text3)", marginBottom: 16 }}>
                      Connect one or more GitHub accounts with OAuth, then choose which account to use for each MCP deploy.
                    </p>
                    <button className="btn btn-primary" onClick={connectGitHub}>
                      Connect GitHub With OAuth
                    </button>
                  </div>
                ) : (
                  <div id="github-connected-display">
                    <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
                      <select
                        className="form-select"
                        value={selectedConnectionId}
                        onChange={(event) => setSelectedConnectionId(event.target.value)}
                        style={{ marginBottom: 0 }}
                      >
                        {githubConnections.map((connection) => (
                          <option key={connection.id} value={connection.id}>
                            @{connection.github_username}
                          </option>
                        ))}
                      </select>
                      <button className="btn btn-secondary btn-sm" onClick={connectGitHub}>
                        Add Account
                      </button>
                      <button className="btn btn-secondary btn-sm" onClick={disconnectGitHub}>
                        Disconnect
                      </button>
                    </div>
                    <div className="github-connected">
                      <span>●</span>
                      <span id="github-user-display">
                        Using @{githubUser?.login} for this deploy
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div className="card" style={{ marginBottom: 20 }} id="repo-select-card">
                <div className="card-header">
                  <div className="card-title">② Select Repository</div>
                  <button className="btn btn-secondary btn-sm" onClick={() => loadRepos()} id="refresh-repos-btn">
                    {reposLoading ? "Loading..." : "↻ Refresh"}
                  </button>
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <select
                    className="form-select"
                    id="repo-dropdown"
                    value={selectedRepoFullName}
                    onChange={(event) => onRepoSelected(event.target.value)}
                    style={{ marginBottom: 12 }}
                  >
                    {!githubConnected ? (
                      <option value="">— Connect GitHub first to see your repos —</option>
                    ) : !selectedConnectionId ? (
                      <option value="">— Select a GitHub account first —</option>
                    ) : reposLoading ? (
                      <option value="">Loading repos...</option>
                    ) : (
                      <>
                        <option value="">— Select a repository —</option>
                        {repos.map((repo) => (
                          <option key={repo.id} value={repo.full_name}>
                            {repo.full_name} {repo.private ? "🔒" : ""}
                          </option>
                        ))}
                      </>
                    )}
                  </select>

                  {selectedRepoMeta && (
                    <div id="repo-details">
                      <div className="repo-item selected" id="repo-detail-card">
                        <div>
                          <div className="repo-name" id="repo-detail-name">
                            {selectedRepoMeta.full_name}
                          </div>
                          <div className="repo-desc" id="repo-detail-desc">
                            {selectedRepoMeta.description || "No description"}
                          </div>
                        </div>
                        <div className="repo-lang" id="repo-detail-lang">
                          {selectedRepoMeta.language || "Unknown"}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="card" style={{ marginBottom: 20 }} id="entry-file-card">
                <div className="card-header">
                  <div className="card-title">③ Select Entry File (main.py)</div>
                </div>
                <p style={{ fontSize: 13, color: "var(--text3)", marginBottom: 14 }}>
                  Select the Python file that starts your MCP server. Usually {" "}
                  <code
                    style={{
                      color: "var(--accent2)",
                      background: "var(--surface2)",
                      padding: "1px 5px",
                      borderRadius: 3,
                    }}
                  >
                    main.py
                  </code>{" "}
                  or {" "}
                  <code
                    style={{
                      color: "var(--accent2)",
                      background: "var(--surface2)",
                      padding: "1px 5px",
                      borderRadius: 3,
                    }}
                  >
                    server.py
                  </code>
                </p>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <select
                    className="form-select"
                    id="entry-file-dropdown"
                    value={selectedEntryFile}
                    onChange={(event) => setSelectedEntryFile(event.target.value)}
                    disabled={!selectedRepoFullName || entryFileLoading}
                  >
                    {!selectedRepoFullName ? (
                      <option value="">— Select a repo first —</option>
                    ) : entryFileLoading ? (
                      <option value="">Loading files...</option>
                    ) : entryFiles.length === 0 ? (
                      <option value="">No Python files found</option>
                    ) : (
                      <>
                        <option value="">— Select entry file —</option>
                        {entryFiles.map((file) => {
                          const suggested = /\b(main|server|app)\b/.test(file);
                          return (
                            <option key={file} value={file}>
                              {file}
                              {suggested ? " ✦ suggested" : ""}
                            </option>
                          );
                        })}
                      </>
                    )}
                  </select>
                </div>
              </div>

              <div className="card" id="deploy-form-card">
                <div className="card-header">
                  <div className="card-title">④ Configure &amp; Deploy from GitHub</div>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Server Name</label>
                    <input
                      type="text"
                      className="form-input"
                      id="server-name-input"
                      placeholder="e.g. invoice-processor"
                      value={serverName}
                      onChange={(event) => setServerName(event.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Description</label>
                    <input
                      type="text"
                      className="form-input"
                      id="server-desc-input"
                      placeholder="What does this MCP do?"
                      value={serverDesc}
                      onChange={(event) => setServerDesc(event.target.value)}
                    />
                  </div>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Runtime Port</label>
                    <input
                      type="number"
                      className="form-input"
                      min="1"
                      max="65535"
                      placeholder="8000"
                      value={runtimePort}
                      onChange={(event) => setRuntimePort(event.target.value)}
                    />
                    <div style={{ marginTop: 8, fontSize: 12, color: "var(--text3)" }}>
                      Set this to the port your MCP container listens on internally.
                    </div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Access Groups</label>
                    <select
                      multiple
                      className="form-select"
                      value={selectedDeployGroupIds}
                      onChange={(event) => {
                        setSelectedDeployGroupIds(Array.from(event.target.selectedOptions).map((option) => option.value));
                      }}
                      style={{ minHeight: 120 }}
                    >
                      {accessGroups.length === 0 ? (
                        <option value="">No access groups yet</option>
                      ) : (
                        accessGroups.map((group) => (
                          <option key={group.id} value={group.id}>
                            {group.name} ({group.member_count})
                          </option>
                        ))
                      )}
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Allowed Google User Emails</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="user1@gmail.com, user2@company.com"
                    value={allowedEmailsInput}
                    onChange={(event) => setAllowedEmailsInput(event.target.value)}
                  />
                  <div style={{ marginTop: 8, fontSize: 12, color: "var(--text3)" }}>
                    Only these users, the deploy owner, and admins can access this MCP.
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Optional Runtime Environment Variables</label>
                  <textarea
                    className="form-input"
                    placeholder={"API_KEY=your-secret\nBASE_URL=https://api.example.com"}
                    value={runtimeEnvInput}
                    onChange={(event) => setRuntimeEnvInput(event.target.value)}
                    style={{ minHeight: 120, resize: "vertical", fontFamily: "var(--mono)", fontSize: 12 }}
                  />
                  <div style={{ marginTop: 8, fontSize: 12, color: "var(--text3)" }}>
                    Leave this empty unless your repo requires startup config. Use one <code>KEY=value</code> per line.
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={deployMCP}
                  id="deploy-btn"
                  style={{ width: "100%", justifyContent: "center" }}
                  disabled={deploying}
                >
                  {deploying ? "⏳ Deploying..." : "🚀 Deploy MCP Server"}
                </button>
              </div>

              <div className="card" style={{ marginTop: 20 }}>
                <div className="card-header">
                  <div className="card-title">⑤ External / Public MCP Import</div>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Display Name</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. docs-search-gateway"
                      value={externalImportName}
                      onChange={(event) => setExternalImportName(event.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Description</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Wrapped external MCP target"
                      value={externalImportDescription}
                      onChange={(event) => setExternalImportDescription(event.target.value)}
                    />
                  </div>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Allowed User Emails</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="user1@gmail.com, user2@company.com"
                      value={externalAllowedEmailsInput}
                      onChange={(event) => setExternalAllowedEmailsInput(event.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Access Groups</label>
                    <select
                      multiple
                      className="form-select"
                      value={externalSelectedGroupIds}
                      onChange={(event) => {
                        setExternalSelectedGroupIds(Array.from(event.target.selectedOptions).map((option) => option.value));
                      }}
                      style={{ minHeight: 120 }}
                    >
                      {accessGroups.length === 0 ? (
                        <option value="">No access groups yet</option>
                      ) : (
                        accessGroups.map((group) => (
                          <option key={group.id} value={group.id}>
                            {group.name} ({group.member_count})
                          </option>
                        ))
                      )}
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">External MCP JSON Config</label>
                  <textarea
                    className="form-input"
                    value={externalImportJson}
                    onChange={(event) => setExternalImportJson(event.target.value)}
                    style={{ minHeight: 210, resize: "vertical", fontFamily: "var(--mono)", fontSize: 12 }}
                  />
                  <div style={{ marginTop: 8, fontSize: 12, color: "var(--text3)" }}>
                    Accepts `upstream_url` or a full `mcpServers.*.serverUrl` JSON block. The gateway will wrap this target with Keycloak auth, group/email access, and audit logs.
                  </div>
                </div>
                <button
                  className="btn btn-secondary"
                  onClick={importExternalMCP}
                  style={{ width: "100%", justifyContent: "center" }}
                  disabled={externalImporting}
                >
                  {externalImporting ? "⏳ Importing..." : "↗ Import External MCP"}
                </button>
              </div>

              {deployResult && (
                <div id="deploy-result" style={{ marginTop: 20 }}>
                  <div className="card" style={{ borderColor: "var(--green)" }}>
                    <div className="card-header">
                      <div className="card-title" style={{ color: "var(--green)" }}>
                        ✅ MCP Server {deployResult.ready ? "Live" : "Deploying..."}
                      </div>
                    </div>

                    <div className="url-box">
                      <div className="url-label">MCP URL</div>
                      <div className="url-value" id="result-mcp-url">
                        {deployResult.mcpUrl}
                      </div>
                      <button className="copy-btn" onClick={() => copyText(deployResult.mcpUrl)}>
                        Copy
                      </button>
                    </div>
                    {deployResult.allowedEmails?.length > 0 && (
                      <div style={{ marginTop: 12, fontSize: 12, color: "var(--text3)" }}>
                        Shared with: {deployResult.allowedEmails.join(", ")}
                      </div>
                    )}
                    {deployResult.allowedGroupIds?.length > 0 && (
                      <div style={{ marginTop: 8, fontSize: 12, color: "var(--text3)" }}>
                        Group access: {deployResult.allowedGroupIds.map((groupId) => accessGroupNameById[groupId] || groupId).join(", ")}
                      </div>
                    )}
                    <div style={{ marginTop: 14, fontSize: 13, color: "var(--text3)" }}>
                      Use this MCP URL in your client. Google/SSO is enforced, access is checked per allowed email, and usage is tracked per user and per MCP.
                    </div>
                    {deployResult.clientConfig && (
                      <div style={{ marginTop: 18 }}>
                        <div
                          style={{
                            fontFamily: "var(--mono)",
                            fontSize: 11,
                            color: "var(--text3)",
                            marginBottom: 8,
                          }}
                        >
                          OAUTH CLIENT CONFIG
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--mono)",
                            fontSize: 11,
                            color: "var(--text2)",
                            background: "var(--bg)",
                            border: "1px solid var(--border)",
                            borderRadius: 8,
                            padding: "12px 14px",
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                          }}
                        >
                          {JSON.stringify(deployResult.clientConfig, null, 2)}
                        </div>
                        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10 }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => copyText(JSON.stringify(deployResult.clientConfig, null, 2), "Client config copied")}
                          >
                            Copy Client Config
                          </button>
                        </div>
                      </div>
                    )}

                    <div style={{ marginTop: 16 }}>
                      <div
                        style={{
                          fontFamily: "var(--mono)",
                          fontSize: 11,
                          color: "var(--text3)",
                          marginBottom: 8,
                        }}
                      >
                        LIVE LOGS
                      </div>
                      <div className="terminal">
                        <div className="terminal-bar">
                          <div className="term-dot red" />
                          <div className="term-dot yellow" />
                          <div className="term-dot green" />
                          <span className="terminal-title" id="terminal-server-name">
                            {deployResult.serverName}
                          </span>
                          <div className="terminal-live">
                            <div
                              style={{
                                width: 6,
                                height: 6,
                                background: "var(--green)",
                                borderRadius: "50%",
                                animation: "pulse 1.5s infinite",
                              }}
                            />
                            LIVE
                          </div>
                        </div>
                        <div className="terminal-body" id="deploy-log-output">
                          {deployLogs.length === 0 && (
                            <span className="log-line info">[system] Waiting for deployment...</span>
                          )}
                          {deployLogs.map((line, index) => (
                            <span key={`${line.msg}-${index}`} className={cn("log-line", line.type)}>
                              {line.msg}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className={cn("page", currentPage === "servers" && "active")} id="page-servers">
              <div className="section-header">
                <div>
                  <div className="section-title">MCP Servers</div>
                  <div className="section-sub">All deployed servers with status and endpoints</div>
                </div>
                <button className="btn btn-primary" onClick={() => showPage("deploy")}>
                  ⬡ Deploy New
                </button>
              </div>

              <div id="servers-grid" className="mcp-cards">
                {deployedServers.length === 0 ? (
                  <div className="empty" style={{ gridColumn: "1/-1" }}>
                    <div className="empty-icon">⬡</div>
                    <div className="empty-title">No servers deployed</div>
                    <div className="empty-sub">Deploy your first MCP from GitHub</div>
                  </div>
                ) : (
                  deployedServers.map((server) => (
                    <div className="mcp-card" key={server.id}>
                      <div className="mcp-card-header">
                        <div className="mcp-icon">⬡</div>
                        <div>
                          <div className="mcp-name">{server.name}</div>
                          <div className="mcp-repo">⬡ {server.repo}</div>
                          <div className="mcp-repo" style={{ color: "var(--text3)" }}>
                            📄 {server.entryFile}
                          </div>
                          <div className="mcp-repo" style={{ color: "var(--text3)" }}>
                            {server.sourceType === "external" ? "↗ external target" : "🐳 docker runtime"}
                          </div>
                        </div>
                        <div style={{ marginLeft: "auto" }}>
                          <span className={cn("chip", server.status === "running" ? "chip-green" : "chip-red")}>
                            {server.status === "running" ? "● LIVE" : "○ STOPPED"}
                          </span>
                        </div>
                      </div>

                      <div
                        style={{
                          fontSize: 11,
                          fontFamily: "var(--mono)",
                          color: "var(--text3)",
                          marginBottom: 6,
                        }}
                      >
                        ENDPOINT
                      </div>
                      <div
                        style={{
                          fontSize: 11.5,
                          fontFamily: "var(--mono)",
                          color: "var(--accent2)",
                          background: "var(--bg)",
                          padding: "8px 10px",
                          borderRadius: 6,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          border: "1px solid var(--border)",
                        }}
                      >
                        {server.url}
                      </div>

                      <div style={{ marginTop: 12, display: "grid", gap: 6 }}>
                        <div style={{ fontSize: 12, color: "var(--text3)" }}>
                          Emails: {server.allowedEmails.length > 0 ? server.allowedEmails.join(", ") : "owner/admin only"}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--text3)" }}>
                          Groups: {server.allowedGroupIds.length > 0 ? server.allowedGroupIds.map((groupId) => accessGroupNameById[groupId] || groupId).join(", ") : "none"}
                        </div>
                      </div>

                      <div className="mcp-card-actions">
                        <button className="btn btn-secondary btn-sm" onClick={() => copyServerUrl(server.id)}>
                          Copy URL
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => viewLogs(server.id)}>
                          View Logs
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => openAccessEditor(server)}>
                          Access
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => stopServer(server.id)}
                          style={{ marginLeft: "auto" }}
                        >
                          Stop
                        </button>
                      </div>

                      {expandedAccessServerId === server.id && (
                        <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)", display: "grid", gap: 12 }}>
                          <div className="form-group" style={{ marginBottom: 0 }}>
                            <label className="form-label">Allowed Emails</label>
                            <input
                              type="text"
                              className="form-input"
                              value={serverAccessDrafts[server.id]?.emailsInput || ""}
                              onChange={(event) => {
                                const value = event.target.value;
                                setServerAccessDrafts((current) => ({
                                  ...current,
                                  [server.id]: { ...(current[server.id] || {}), emailsInput: value, groupIds: current[server.id]?.groupIds || server.allowedGroupIds || [], saving: current[server.id]?.saving || false },
                                }));
                              }}
                            />
                          </div>
                          <div className="form-group" style={{ marginBottom: 0 }}>
                            <label className="form-label">Allowed Groups</label>
                            <select
                              multiple
                              className="form-select"
                              value={serverAccessDrafts[server.id]?.groupIds || []}
                              onChange={(event) => {
                                const groupIds = Array.from(event.target.selectedOptions).map((option) => option.value);
                                setServerAccessDrafts((current) => ({
                                  ...current,
                                  [server.id]: { ...(current[server.id] || {}), emailsInput: current[server.id]?.emailsInput || (server.allowedEmails || []).join(", "), groupIds, saving: current[server.id]?.saving || false },
                                }));
                              }}
                              style={{ minHeight: 120 }}
                            >
                              {accessGroups.length === 0 ? (
                                <option value="">No access groups yet</option>
                              ) : (
                                accessGroups.map((group) => (
                                  <option key={group.id} value={group.id}>
                                    {group.name} ({group.member_count})
                                  </option>
                                ))
                              )}
                            </select>
                          </div>
                          <div style={{ display: "flex", justifyContent: "flex-end" }}>
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => saveServerAccess(server.id)}
                              disabled={serverAccessDrafts[server.id]?.saving}
                            >
                              {serverAccessDrafts[server.id]?.saving ? "Saving..." : "Save Access"}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className={cn("page", currentPage === "sessions" && "active")} id="page-sessions">
              <div className="section-header">
                <div>
                  <div className="section-title">Active Sessions</div>
                  <div className="section-sub">
                    {isAdmin ? "Platform-wide sessions across all tenants" : "Real-time user sessions per MCP server"}
                  </div>
                </div>
                <button className="btn btn-secondary btn-sm" onClick={loadSessions}>
                  ↻ Refresh
                </button>
              </div>

              <div className="card">
                <table>
                  <thead>
                    <tr>
                      <th>Session ID</th>
                      <th>User</th>
                      <th>MCP Server</th>
                      <th>Started</th>
                      <th>Calls</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody id="sessions-table">
                    {sessions.length === 0 ? (
                      <tr>
                        <td colSpan={6} style={{ textAlign: "center", color: "var(--text3)", padding: 40 }}>
                          No active sessions
                        </td>
                      </tr>
                    ) : (
                      sessions.map((session) => (
                        <tr key={session.id}>
                          <td>
                            <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>
                              {session.id}
                            </span>
                          </td>
                          <td>{session.email}</td>
                          <td>
                            <span className="chip chip-purple">{session.server}</span>
                          </td>
                          <td style={{ color: "var(--text3)", fontFamily: "var(--mono)", fontSize: 12 }}>
                            {session.started}
                          </td>
                          <td>
                            <span style={{ fontFamily: "var(--mono)" }}>{session.calls}</span>
                          </td>
                          <td>
                            <span className={cn("chip", session.status === "active" ? "chip-green" : "chip-red")}>
                              {session.status === "active" ? "● active" : "stopped"}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className={cn("page", currentPage === "audit" && "active")} id="page-audit">
              <div className="section-header">
                <div>
                  <div className="section-title">Audit Logs</div>
                  <div className="section-sub">
                    {isAdmin ? "Every platform tool call across tenants" : "Every tool call — who, what, when"}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                  <select
                    className="form-select"
                    style={{ width: 180 }}
                    id="audit-filter-user"
                    value={auditFilterUser}
                    onChange={(event) => setAuditFilterUser(event.target.value)}
                  >
                    <option value="">All Users</option>
                    {uniqueAuditUsers.map((user) => (
                      <option key={user} value={user}>
                        {user}
                      </option>
                    ))}
                  </select>
                  <button className="btn btn-secondary btn-sm" onClick={loadAuditLogs}>
                    ↻ Refresh
                  </button>
                </div>
              </div>

              <div className="card">
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>User</th>
                      <th>Tenant</th>
                      <th>Tool Called</th>
                      <th>MCP Server</th>
                      <th>Duration</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody id="audit-table">
                    {filteredAuditLogs.length === 0 ? (
                      <tr>
                        <td colSpan={7} style={{ textAlign: "center", color: "var(--text3)", padding: 40 }}>
                          No audit events yet — tool calls will appear here
                        </td>
                      </tr>
                    ) : (
                      filteredAuditLogs.map((log) => (
                        <tr key={log.id}>
                          <td style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>
                            {log.time}
                          </td>
                          <td style={{ fontSize: 12 }}>{log.user}</td>
                          <td>
                            <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text3)" }}>
                              {log.tenant}
                            </span>
                          </td>
                          <td>
                            <code
                              style={{
                                fontFamily: "var(--mono)",
                                fontSize: 12,
                                color: "var(--accent2)",
                                background: "rgba(0,229,192,0.08)",
                                padding: "2px 7px",
                                borderRadius: 4,
                              }}
                            >
                              {log.tool}
                            </code>
                          </td>
                          <td>
                            <span className="chip chip-purple">{log.server}</span>
                          </td>
                          <td style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text3)" }}>
                            {log.duration}
                          </td>
                          <td>
                            <span className={cn("chip", log.status === "success" ? "chip-green" : "chip-red")}>
                              {log.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className={cn("page", currentPage === "settings" && "active")} id="page-settings">
              <div className="section-header">
                <div>
                  <div className="section-title">OAuth Configuration</div>
                  <div className="section-sub">Keycloak identity server settings</div>
                </div>
              </div>

              <div className="grid-2">
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">Keycloak Settings</div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Keycloak URL</label>
                    <input type="text" className="form-input" value="http://localhost:8080" readOnly />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Realm</label>
                    <input type="text" className="form-input" value="mcp-platform" readOnly />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Client ID</label>
                    <input type="text" className="form-input" value="mcp-frontend" readOnly />
                  </div>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Status</label>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "10px 14px",
                        background: "var(--bg)",
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                      }}
                    >
                      <div className="status-dot" style={{ width: 8, height: 8 }} />
                      <span style={{ fontSize: 13, color: "var(--green)" }}>Running on localhost:8080</span>
                    </div>
                  </div>
                </div>

                <div className="card">
                  <div className="card-header">
                    <div className="card-title">Quick Links</div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <a
                      href="http://localhost:8080"
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-secondary"
                      style={{ textDecoration: "none" }}
                    >
                      🔐 Keycloak Admin Console
                    </a>
                    <a
                      href="http://localhost:8000/docs"
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-secondary"
                      style={{ textDecoration: "none" }}
                    >
                      📡 Backend API Docs (Swagger)
                    </a>
                    <a
                      href="http://localhost:9001"
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-secondary"
                      style={{ textDecoration: "none" }}
                    >
                      🗄️ MinIO File Storage
                    </a>
                    <button type="button" className="btn btn-secondary" onClick={testAPI}>
                      ⚡ Test API Connection
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={connectGitHub}>
                      ↗ Connect GitHub OAuth
                    </button>
                    <button type="button" className="btn btn-danger" onClick={() => logout(true)}>
                      Sign Out
                    </button>
                  </div>

                  <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
                    <div className="card-title" style={{ marginBottom: 12 }}>
                      AWS Migration (Later)
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text3)", lineHeight: 1.8 }}>
                      <div>Keycloak → AWS Cognito</div>
                      <div>PostgreSQL → AWS RDS</div>
                      <div>Redis → AWS ElastiCache</div>
                      <div>MinIO → AWS S3</div>
                      <div style={{ marginTop: 8, color: "var(--text2)" }}>
                        Zero code changes — just swap env vars
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="card" style={{ marginTop: 20 }}>
                <div className="card-header">
                  <div>
                    <div className="card-title">Access Groups</div>
                    <div className="section-sub">Create reusable email groups, then attach them to MCP servers</div>
                  </div>
                  <button className="btn btn-secondary btn-sm" onClick={() => loadAccessGroups(false)}>
                    ↻ Refresh
                  </button>
                </div>

                <div className="grid-2">
                  <div>
                    <div className="form-group">
                      <label className="form-label">Group Name</label>
                      <input
                        type="text"
                        className="form-input"
                        value={groupEditor.name}
                        onChange={(event) => setGroupEditor((current) => ({ ...current, name: event.target.value }))}
                        placeholder="e.g. Customer Success"
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Description</label>
                      <input
                        type="text"
                        className="form-input"
                        value={groupEditor.description}
                        onChange={(event) => setGroupEditor((current) => ({ ...current, description: event.target.value }))}
                        placeholder="Who should use this MCP?"
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Member Emails</label>
                      <textarea
                        className="form-input"
                        value={groupEditor.members}
                        onChange={(event) => setGroupEditor((current) => ({ ...current, members: event.target.value }))}
                        placeholder="alice@company.com, bob@company.com"
                        style={{ minHeight: 120, resize: "vertical" }}
                      />
                    </div>
                    <div style={{ display: "flex", gap: 10 }}>
                      <button className="btn btn-primary" onClick={saveAccessGroup}>
                        {groupEditor.id ? "Update Group" : "Create Group"}
                      </button>
                      {groupEditor.id && (
                        <button
                          className="btn btn-secondary"
                          onClick={() => setGroupEditor({ id: "", name: "", description: "", members: "" })}
                        >
                          Cancel Edit
                        </button>
                      )}
                    </div>
                  </div>

                  <div style={{ display: "grid", gap: 12 }}>
                    {accessGroups.length === 0 ? (
                      <div className="empty">
                        <div className="empty-icon">◎</div>
                        <div className="empty-title">No access groups yet</div>
                        <div className="empty-sub">Create a reusable group to grant MCP access faster.</div>
                      </div>
                    ) : (
                      accessGroups.map((group) => (
                        <div key={group.id} className="repo-item selected" style={{ alignItems: "flex-start" }}>
                          <div style={{ display: "grid", gap: 6, flex: 1 }}>
                            <div className="repo-name">{group.name}</div>
                            <div className="repo-desc">{group.description || "No description"}</div>
                            <div style={{ fontSize: 12, color: "var(--text3)" }}>
                              {group.member_count} member{group.member_count === 1 ? "" : "s"}
                            </div>
                            <div style={{ fontSize: 12, color: "var(--text3)", lineHeight: 1.6 }}>
                              {(group.members || []).join(", ") || "No members"}
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: 8 }}>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => setGroupEditor({
                                id: group.id,
                                name: group.name,
                                description: group.description || "",
                                members: (group.members || []).join(", "),
                              })}
                            >
                              Edit
                            </button>
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => deleteAccessGroup(group.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        className={cn("notif", notif.show && "show")}
        id="notif"
        style={{
          borderColor: notif.isError ? "var(--red)" : "var(--green)",
          color: notif.isError ? "var(--red)" : "var(--green)",
        }}
      >
        {notif.text}
      </div>
    </>
  );
}
