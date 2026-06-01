import { useMemo, useState } from "react";
import { Badge, Card } from "../../components/ui";
import { useHealth } from "../../hooks/useMarketData";

/* ─── TABS ─── */
const TABS = [
  "Dashboard",
  "Users",
  "Access Log",
  "Security",
  "Quick Invite",
] as const;
type Tab = (typeof TABS)[number];

/* ─── DATA ─── */
const SYSTEM_STATUS = [
  {
    label: "Total Users",
    value: "8",
    detail: "3 admin, 5 analyst",
    color: "#00D9FF",
  },
  { label: "Active Now", value: "3", detail: "last 24 h", color: "#10B981" },
  { label: "Live Sessions", value: "2", detail: "of 10 max", color: "#D4AF37" },
  { label: "Uptime", value: "99.97%", detail: "45 days", color: "#10B981" },
  {
    label: "Cache Hit Rate",
    value: "94.2%",
    detail: "Redis",
    color: "#D4AF37",
  },
  { label: "API Latency", value: "42ms", detail: "p95", color: "#10B981" },
];

const USERS = [
  {
    id: 1,
    name: "Matthias Raven",
    email: "matthias@ravinala.io",
    role: "Admin",
    lastLogin: "2026-03-22 09:15",
    status: "Active" as const,
    loginCount: 342,
    expiry: "2027-01-01",
  },
  {
    id: 2,
    name: "Sarah Chen",
    email: "sarah@ravinala.io",
    role: "Analyst",
    lastLogin: "2026-03-22 08:42",
    status: "Active" as const,
    loginCount: 214,
    expiry: "2026-12-15",
  },
  {
    id: 3,
    name: "Alex Morgan",
    email: "alex@ravinala.io",
    role: "Trader",
    lastLogin: "2026-03-21 17:30",
    status: "Inactive" as const,
    loginCount: 89,
    expiry: "2026-04-01",
  },
  {
    id: 4,
    name: "Julie Martin",
    email: "julie@ravinala.io",
    role: "Analyst",
    lastLogin: "2026-03-20 14:12",
    status: "Active" as const,
    loginCount: 156,
    expiry: "2026-09-30",
  },
  {
    id: 5,
    name: "Tom Bernard",
    email: "tom@ravinala.io",
    role: "Viewer",
    lastLogin: "2026-03-18 11:05",
    status: "Inactive" as const,
    loginCount: 22,
    expiry: "2026-04-15",
  },
  {
    id: 6,
    name: "Léa Dupont",
    email: "lea@ravinala.io",
    role: "Admin",
    lastLogin: "2026-03-22 07:55",
    status: "Active" as const,
    loginCount: 410,
    expiry: "2027-03-01",
  },
  {
    id: 7,
    name: "Kenji Tanaka",
    email: "kenji@ravinala.io",
    role: "Analyst",
    lastLogin: "2026-03-19 16:33",
    status: "Active" as const,
    loginCount: 78,
    expiry: "2026-11-20",
  },
  {
    id: 8,
    name: "Nina Petrova",
    email: "nina@ravinala.io",
    role: "Trader",
    lastLogin: "2026-03-17 09:20",
    status: "Inactive" as const,
    loginCount: 45,
    expiry: "2026-03-25",
  },
];

const RECENT_ACTIVITY = [
  {
    ts: "2026-03-22 09:15:02",
    user: "Matthias Raven",
    action: "Login",
    success: true,
    detail: "Chrome / Windows",
  },
  {
    ts: "2026-03-22 08:42:11",
    user: "Sarah Chen",
    action: "Login",
    success: true,
    detail: "Firefox / macOS",
  },
  {
    ts: "2026-03-22 07:55:44",
    user: "Léa Dupont",
    action: "Login",
    success: true,
    detail: "Safari / macOS",
  },
  {
    ts: "2026-03-21 23:10:08",
    user: "unknown",
    action: "Login attempt",
    success: false,
    detail: "Invalid credentials — IP 45.33.12.99",
  },
  {
    ts: "2026-03-21 17:30:22",
    user: "Alex Morgan",
    action: "Logout",
    success: true,
    detail: "Session ended",
  },
  {
    ts: "2026-03-21 14:05:30",
    user: "Matthias Raven",
    action: "User created",
    success: true,
    detail: "Created account for Nina Petrova",
  },
  {
    ts: "2026-03-21 12:00:00",
    user: "System",
    action: "Password reset",
    success: true,
    detail: "Reset for Tom Bernard",
  },
  {
    ts: "2026-03-20 14:12:55",
    user: "Julie Martin",
    action: "Login",
    success: true,
    detail: "Edge / Windows",
  },
  {
    ts: "2026-03-20 10:45:10",
    user: "Léa Dupont",
    action: "Role change",
    success: true,
    detail: "Kenji Tanaka: Viewer → Analyst",
  },
  {
    ts: "2026-03-19 22:00:01",
    user: "System",
    action: "Expiry warning",
    success: true,
    detail: "Nina Petrova expires in 5 days",
  },
  {
    ts: "2026-03-19 16:33:44",
    user: "Kenji Tanaka",
    action: "Login",
    success: true,
    detail: "Chrome / Linux",
  },
  {
    ts: "2026-03-18 11:05:02",
    user: "Tom Bernard",
    action: "Login",
    success: true,
    detail: "Chrome / Windows",
  },
];

const ACCESS_LOG = RECENT_ACTIVITY; // same data, used in Access Log tab with filtering

/* ─── Helpers ─── */
const daysUntil = (d: string) =>
  Math.ceil((new Date(d).getTime() - Date.now()) / 86400000);

const btnStyle = (color: string): React.CSSProperties => ({
  padding: "4px 10px",
  borderRadius: 6,
  fontSize: 11,
  fontWeight: 600,
  cursor: "pointer",
  border: `1px solid ${color}33`,
  backgroundColor: `${color}18`,
  color,
});

export default function AdminPanel() {
  const { data: healthData } = useHealth();
  const [tab, setTab] = useState<Tab>("Dashboard");

  /* ── Users tab state ── */
  const [userStatuses, setUserStatuses] = useState<
    Record<number, "Active" | "Inactive">
  >(() => Object.fromEntries(USERS.map((u) => [u.id, u.status])));
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState("Analyst");

  /* ── Access Log state ── */
  const [logFilter, setLogFilter] = useState("");
  const [logRows, setLogRows] = useState(50);

  /* ── Security state ── */
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");

  /* ── Quick Invite state ── */
  const [invName, setInvName] = useState("");
  const [invEmail, setInvEmail] = useState("");
  const [invDays, setInvDays] = useState(30);
  const [invResult, setInvResult] = useState<{
    user: string;
    pass: string;
  } | null>(null);

  /* filtered access log */
  const filteredLog = useMemo(() => {
    const rows = logFilter
      ? ACCESS_LOG.filter(
          (r) =>
            r.user.toLowerCase().includes(logFilter.toLowerCase()) ||
            r.action.toLowerCase().includes(logFilter.toLowerCase()),
        )
      : ACCESS_LOG;
    return rows.slice(0, logRows);
  }, [logFilter, logRows]);

  /* expiring soon */
  const expiring = USERS.filter(
    (u) => daysUntil(u.expiry) <= 30 && daysUntil(u.expiry) > 0,
  );

  const Toggle = ({
    checked,
    onChange,
  }: {
    checked: boolean;
    onChange: () => void;
  }) => (
    <div
      onClick={onChange}
      style={{
        width: 40,
        height: 22,
        borderRadius: 11,
        cursor: "pointer",
        backgroundColor: checked ? "#10B981" : "rgba(51,65,85,0.5)",
        position: "relative",
        transition: "background-color 0.2s",
      }}
    >
      <div
        style={{
          width: 18,
          height: 18,
          borderRadius: 9,
          backgroundColor: "#F1F5F9",
          position: "absolute",
          top: 2,
          left: checked ? 20 : 2,
          transition: "left 0.2s",
        }}
      />
    </div>
  );

  const inputStyle: React.CSSProperties = {
    backgroundColor: "#131823",
    border: "1px solid rgba(51,65,85,0.5)",
    borderRadius: 8,
    padding: "8px 12px",
    color: "#F1F5F9",
    fontSize: 13,
    outline: "none",
    width: "100%",
  };

  return (
    <div style={{ color: "#F1F5F9" }}>
      {!healthData && (
        <div
          style={{
            background: "rgba(245,158,11,0.15)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 8,
            padding: "8px 16px",
            marginBottom: 16,
            fontSize: 13,
            color: "#F59E0B",
            fontFamily: "Inter, sans-serif",
          }}
        >
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 4,
          color: "#F97316",
        }}
      >
        Admin Panel
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        System administration, users & security
        {healthData && (
          <span
            style={{
              marginLeft: 12,
              fontSize: 12,
              color: healthData.status === "ok" ? "#10B981" : "#EF4444",
            }}
          >
            Backend: {healthData.status} · Redis:{" "}
            {healthData.redis_connected ? "connected" : "disconnected"} · Data
            service: {healthData.data_service_ok ? "OK" : "down"}
          </span>
        )}
      </p>

      {/* Tab bar */}
      <div
        style={{ display: "flex", gap: 4, marginBottom: 16, flexWrap: "wrap" }}
      >
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "8px 14px",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              border:
                tab === t
                  ? "1px solid rgba(212,175,55,0.5)"
                  : "1px solid rgba(51,65,85,0.3)",
              backgroundColor:
                tab === t ? "rgba(212,175,55,0.15)" : "rgba(15,23,42,0.5)",
              color: tab === t ? "#D4AF37" : "#94A3B8",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ═══════ DASHBOARD ═══════ */}
      {tab === "Dashboard" && (
        <>
          {/* Metrics */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
              gap: 10,
              marginBottom: 16,
            }}
          >
            {SYSTEM_STATUS.map((s) => (
              <Card key={s.label}>
                <div
                  style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}
                >
                  {s.label}
                </div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    fontFamily: "JetBrains Mono, monospace",
                    color: s.color,
                  }}
                >
                  {s.value}
                </div>
                <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                  {s.detail}
                </div>
              </Card>
            ))}
          </div>

          {/* Expiring soon */}
          {expiring.length > 0 && (
            <Card title="⚠ Expiring Soon">
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {expiring.map((u) => (
                  <div
                    key={u.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "6px 0",
                      borderBottom: "1px solid rgba(51,65,85,0.2)",
                    }}
                  >
                    <div>
                      <span
                        style={{
                          color: "#F1F5F9",
                          fontWeight: 500,
                          fontSize: 13,
                        }}
                      >
                        {u.name}
                      </span>
                      <span
                        style={{
                          color: "#64748B",
                          fontSize: 12,
                          marginLeft: 8,
                        }}
                      >
                        {u.role}
                      </span>
                    </div>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <span
                        style={{
                          fontFamily: "JetBrains Mono, monospace",
                          fontSize: 12,
                          color:
                            daysUntil(u.expiry) <= 7 ? "#EF4444" : "#F59E0B",
                        }}
                      >
                        {daysUntil(u.expiry)}d left
                      </span>
                      <button style={btnStyle("#10B981")}>Extend +30d</button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Recent Activity */}
          <Card title="Recent Activity" subtitle="Last 12 events">
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 12,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {["Timestamp", "User", "Action", "Status", "Details"].map(
                      (h) => (
                        <th
                          key={h}
                          style={{
                            padding: "6px 8px",
                            textAlign: "left",
                            color: "#94A3B8",
                            fontWeight: 500,
                          }}
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {RECENT_ACTIVITY.slice(0, 12).map((r, i) => (
                    <tr
                      key={i}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td
                        style={{
                          padding: "6px 8px",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#64748B",
                          fontSize: 11,
                        }}
                      >
                        {r.ts}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          color: "#F1F5F9",
                          fontWeight: 500,
                        }}
                      >
                        {r.user}
                      </td>
                      <td style={{ padding: "6px 8px", color: "#94A3B8" }}>
                        {r.action}
                      </td>
                      <td style={{ padding: "6px 8px" }}>
                        <Badge variant={r.success ? "up" : "down"}>
                          {r.success ? "OK" : "FAIL"}
                        </Badge>
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          color: "#64748B",
                          maxWidth: 250,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {r.detail}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ═══════ USERS ═══════ */}
      {tab === "Users" && (
        <>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            <span style={{ color: "#94A3B8", fontSize: 13 }}>
              {USERS.length} registered accounts
            </span>
            <button
              onClick={() => setShowCreate(!showCreate)}
              style={btnStyle("#D4AF37")}
            >
              {showCreate ? "Cancel" : "+ New User"}
            </button>
          </div>

          {showCreate && (
            <Card title="Create New User">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: 12,
                  marginBottom: 12,
                }}
              >
                <div>
                  <label
                    style={{
                      fontSize: 11,
                      color: "#64748B",
                      display: "block",
                      marginBottom: 4,
                    }}
                  >
                    Full Name
                  </label>
                  <input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    style={inputStyle}
                    placeholder="Jane Doe"
                  />
                </div>
                <div>
                  <label
                    style={{
                      fontSize: 11,
                      color: "#64748B",
                      display: "block",
                      marginBottom: 4,
                    }}
                  >
                    Email
                  </label>
                  <input
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    style={inputStyle}
                    placeholder="jane@ravinala.io"
                  />
                </div>
                <div>
                  <label
                    style={{
                      fontSize: 11,
                      color: "#64748B",
                      display: "block",
                      marginBottom: 4,
                    }}
                  >
                    Role
                  </label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    style={inputStyle}
                  >
                    {["Admin", "Analyst", "Trader", "Viewer"].map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                style={{
                  ...btnStyle("#10B981"),
                  padding: "8px 20px",
                  fontSize: 13,
                }}
              >
                Create Account
              </button>
            </Card>
          )}

          <Card>
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {[
                      "Name",
                      "Role",
                      "Logins",
                      "Last Login",
                      "Expiry",
                      "Status",
                      "Actions",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "8px 10px",
                          textAlign: "left",
                          color: "#94A3B8",
                          fontWeight: 500,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {USERS.map((u) => {
                    const active = userStatuses[u.id] === "Active";
                    const dLeft = daysUntil(u.expiry);
                    return (
                      <tr
                        key={u.id}
                        style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                      >
                        <td style={{ padding: "8px 10px" }}>
                          <div style={{ color: "#F1F5F9", fontWeight: 500 }}>
                            {u.name}
                          </div>
                          <div style={{ color: "#64748B", fontSize: 11 }}>
                            {u.email}
                          </div>
                        </td>
                        <td style={{ padding: "8px 10px" }}>
                          <Badge variant="info">{u.role}</Badge>
                        </td>
                        <td
                          style={{
                            padding: "8px 10px",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#94A3B8",
                            fontSize: 12,
                          }}
                        >
                          {u.loginCount}
                        </td>
                        <td
                          style={{
                            padding: "8px 10px",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#94A3B8",
                            fontSize: 11,
                          }}
                        >
                          {u.lastLogin}
                        </td>
                        <td
                          style={{
                            padding: "8px 10px",
                            fontFamily: "JetBrains Mono, monospace",
                            fontSize: 11,
                            color:
                              dLeft <= 7
                                ? "#EF4444"
                                : dLeft <= 30
                                  ? "#F59E0B"
                                  : "#94A3B8",
                          }}
                        >
                          {u.expiry}{" "}
                          <span style={{ fontSize: 10 }}>({dLeft}d)</span>
                        </td>
                        <td style={{ padding: "8px 10px" }}>
                          <Badge variant={active ? "up" : "neutral"}>
                            {active ? "Active" : "Inactive"}
                          </Badge>
                        </td>
                        <td style={{ padding: "8px 10px" }}>
                          <div
                            style={{
                              display: "flex",
                              gap: 4,
                              flexWrap: "wrap",
                            }}
                          >
                            <button
                              onClick={() =>
                                setUserStatuses((p) => ({
                                  ...p,
                                  [u.id]: active ? "Inactive" : "Active",
                                }))
                              }
                              style={btnStyle(active ? "#EF4444" : "#10B981")}
                            >
                              {active ? "Disable" : "Enable"}
                            </button>
                            <button style={btnStyle("#F59E0B")}>
                              Reset PW
                            </button>
                            <button style={btnStyle("#00D9FF")}>+30d</button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ═══════ ACCESS LOG ═══════ */}
      {tab === "Access Log" && (
        <>
          <div
            style={{
              display: "flex",
              gap: 12,
              marginBottom: 16,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <input
              value={logFilter}
              onChange={(e) => setLogFilter(e.target.value)}
              placeholder="Filter by user or action…"
              style={{ ...inputStyle, flex: "1 1 250px", maxWidth: 400 }}
            />
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 12, color: "#64748B" }}>Rows:</span>
              <select
                value={logRows}
                onChange={(e) => setLogRows(Number(e.target.value))}
                style={{ ...inputStyle, width: 80 }}
              >
                {[10, 25, 50, 100, 500].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>
            <button style={btnStyle("#00D9FF")}>Export CSV</button>
          </div>

          <Card>
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 12,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {[
                      "Timestamp",
                      "Username",
                      "Action",
                      "Success",
                      "Details",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 8px",
                          textAlign: "left",
                          color: "#94A3B8",
                          fontWeight: 500,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredLog.map((r, i) => (
                    <tr
                      key={i}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td
                        style={{
                          padding: "6px 8px",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#64748B",
                          fontSize: 11,
                        }}
                      >
                        {r.ts}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          color: "#F1F5F9",
                          fontWeight: 500,
                        }}
                      >
                        {r.user}
                      </td>
                      <td style={{ padding: "6px 8px", color: "#94A3B8" }}>
                        {r.action}
                      </td>
                      <td style={{ padding: "6px 8px" }}>
                        <Badge variant={r.success ? "up" : "down"}>
                          {r.success ? "✓" : "✗"}
                        </Badge>
                      </td>
                      <td style={{ padding: "6px 8px", color: "#64748B" }}>
                        {r.detail}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{ color: "#64748B", fontSize: 11, marginTop: 8 }}>
              Showing {filteredLog.length} of {ACCESS_LOG.length} entries
            </p>
          </Card>
        </>
      )}

      {/* ═══════ SECURITY ═══════ */}
      {tab === "Security" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
              gap: 16,
            }}
          >
            {/* Global logout */}
            <Card title="Session Management">
              <p style={{ color: "#94A3B8", fontSize: 13, marginBottom: 12 }}>
                Force-terminate all active user sessions across the platform.
              </p>
              <button
                style={{
                  ...btnStyle("#EF4444"),
                  padding: "10px 24px",
                  fontSize: 13,
                }}
              >
                Logout ALL Users
              </button>
              <div style={{ marginTop: 16 }}>
                <p style={{ color: "#64748B", fontSize: 12, marginBottom: 4 }}>
                  Active sessions:{" "}
                  <span
                    style={{
                      color: "#F1F5F9",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    2
                  </span>
                </p>
                <p style={{ color: "#64748B", fontSize: 12 }}>
                  Max concurrent:{" "}
                  <span
                    style={{
                      color: "#F1F5F9",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    10
                  </span>
                </p>
              </div>
            </Card>

            {/* Change admin password */}
            <Card title="Change Admin Password">
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  maxWidth: 350,
                }}
              >
                <div>
                  <label
                    style={{
                      fontSize: 11,
                      color: "#64748B",
                      display: "block",
                      marginBottom: 4,
                    }}
                  >
                    Current Password
                  </label>
                  <input
                    type="password"
                    value={oldPw}
                    onChange={(e) => setOldPw(e.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label
                    style={{
                      fontSize: 11,
                      color: "#64748B",
                      display: "block",
                      marginBottom: 4,
                    }}
                  >
                    New Password
                  </label>
                  <input
                    type="password"
                    value={newPw}
                    onChange={(e) => setNewPw(e.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label
                    style={{
                      fontSize: 11,
                      color: "#64748B",
                      display: "block",
                      marginBottom: 4,
                    }}
                  >
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    value={confirmPw}
                    onChange={(e) => setConfirmPw(e.target.value)}
                    style={inputStyle}
                  />
                </div>
                {newPw && confirmPw && newPw !== confirmPw && (
                  <p style={{ color: "#EF4444", fontSize: 12 }}>
                    Passwords do not match
                  </p>
                )}
                <button
                  style={{
                    ...btnStyle("#D4AF37"),
                    padding: "8px 20px",
                    fontSize: 13,
                    alignSelf: "flex-start",
                  }}
                >
                  Update Password
                </button>
              </div>
            </Card>

            {/* Security toggles */}
            <Card title="Protection Settings">
              <div
                style={{ display: "flex", flexDirection: "column", gap: 14 }}
              >
                {[
                  {
                    label: "Two-Factor Auth",
                    desc: "Require 2FA for all logins",
                  },
                  {
                    label: "IP Allowlist",
                    desc: "Restrict access to known IPs only",
                  },
                  {
                    label: "Session Timeout",
                    desc: "Auto-logout after 30 min idle",
                  },
                  { label: "Audit Logging", desc: "Record all admin actions" },
                ].map((s, i) => (
                  <div
                    key={s.label}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          color: "#F1F5F9",
                          fontSize: 13,
                          fontWeight: 500,
                        }}
                      >
                        {s.label}
                      </div>
                      <div style={{ color: "#64748B", fontSize: 11 }}>
                        {s.desc}
                      </div>
                    </div>
                    <Toggle checked={i < 2} onChange={() => {}} />
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}

      {/* ═══════ QUICK INVITE ═══════ */}
      {tab === "Quick Invite" && (
        <>
          <Card
            title="Quick User Invite"
            subtitle="Generate temporary credentials for a new team member"
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 12,
                marginBottom: 16,
              }}
            >
              <div>
                <label
                  style={{
                    fontSize: 11,
                    color: "#64748B",
                    display: "block",
                    marginBottom: 4,
                  }}
                >
                  Display Name
                </label>
                <input
                  value={invName}
                  onChange={(e) => setInvName(e.target.value)}
                  style={inputStyle}
                  placeholder="Jane Doe"
                />
              </div>
              <div>
                <label
                  style={{
                    fontSize: 11,
                    color: "#64748B",
                    display: "block",
                    marginBottom: 4,
                  }}
                >
                  Email
                </label>
                <input
                  value={invEmail}
                  onChange={(e) => setInvEmail(e.target.value)}
                  style={inputStyle}
                  placeholder="jane@company.com"
                />
              </div>
              <div>
                <label
                  style={{
                    fontSize: 11,
                    color: "#64748B",
                    display: "block",
                    marginBottom: 4,
                  }}
                >
                  Access Duration (days)
                </label>
                <select
                  value={invDays}
                  onChange={(e) => setInvDays(Number(e.target.value))}
                  style={inputStyle}
                >
                  {[7, 14, 30, 60, 90].map((d) => (
                    <option key={d} value={d}>
                      {d} days
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              onClick={() => {
                if (!invName.trim() || !invEmail.trim()) return;
                const user = invEmail
                  .split("@")[0]
                  .toLowerCase()
                  .replace(/[^a-z0-9]/g, "");
                const pass = `Rv${Math.random().toString(36).slice(2, 8)}!${Math.floor(Math.random() * 90 + 10)}`;
                setInvResult({ user, pass });
              }}
              style={{
                ...btnStyle("#10B981"),
                padding: "10px 24px",
                fontSize: 13,
              }}
            >
              Generate Credentials
            </button>

            {invResult && (
              <div
                style={{
                  marginTop: 16,
                  backgroundColor: "rgba(16,185,129,0.08)",
                  border: "1px solid rgba(16,185,129,0.3)",
                  borderRadius: 8,
                  padding: 16,
                }}
              >
                <p
                  style={{
                    color: "#10B981",
                    fontWeight: 600,
                    fontSize: 14,
                    marginBottom: 8,
                  }}
                >
                  Credentials Generated
                </p>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "100px 1fr",
                    gap: "6px 12px",
                    fontSize: 13,
                  }}
                >
                  <span style={{ color: "#64748B" }}>Name:</span>
                  <span style={{ color: "#F1F5F9" }}>{invName}</span>
                  <span style={{ color: "#64748B" }}>Username:</span>
                  <span
                    style={{
                      color: "#D4AF37",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {invResult.user}
                  </span>
                  <span style={{ color: "#64748B" }}>Password:</span>
                  <span
                    style={{
                      color: "#D4AF37",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {invResult.pass}
                  </span>
                  <span style={{ color: "#64748B" }}>Expires:</span>
                  <span style={{ color: "#F1F5F9" }}>
                    {new Date(Date.now() + invDays * 86400000)
                      .toISOString()
                      .slice(0, 10)}{" "}
                    ({invDays} days)
                  </span>
                </div>
                <p style={{ color: "#F59E0B", fontSize: 11, marginTop: 10 }}>
                  Copy these credentials now — the password will not be shown
                  again.
                </p>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
