import api from "./client";

// ── Types ────────────────────────────────────────────────────────────────────

export interface UserInfo {
  id: string;
  email: string;
  username: string;
  role: string;
  created_at: string;
}

export interface UpdateUserRequest {
  name?: string;
  role?: string;
}

export interface AuditEntry {
  id: string;
  user_id: string | null;
  action: string;
  resource: string;
  timestamp: string;
  details?: string;
}

export interface RoleInfo {
  name: string;
  level: number;
  description: string;
}

export interface SecurityStatus {
  security_level: number;
  level_name: string;
  jwt_algorithm: string;
  jwt_expire_minutes: number;
  secret_key_configured: boolean;
  allow_anonymous_readonly_local: boolean;
  allow_public_registration: boolean;
  features: {
    authentication: boolean;
    rbac_enforced: boolean;
    audit_trail: boolean;
    password_hashing: string;
  };
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function fetchUsers(): Promise<UserInfo[]> {
  const { data } = await api.get("/api/v1/users");
  return data;
}

export async function fetchUser(userId: string): Promise<UserInfo> {
  const { data } = await api.get(`/api/v1/users/${userId}`);
  return data;
}

export async function updateUser(
  userId: string,
  update: UpdateUserRequest,
): Promise<UserInfo> {
  const { data } = await api.put(`/api/v1/users/${userId}`, update);
  return data;
}

export async function deleteUser(userId: string): Promise<void> {
  await api.delete(`/api/v1/users/${userId}`);
}

export async function fetchRoles(): Promise<RoleInfo[]> {
  const { data } = await api.get<{ roles: RoleInfo[] }>("/api/v1/roles");
  return data.roles ?? [];
}

export async function fetchAuditTrail(): Promise<AuditEntry[]> {
  const { data } = await api.get<{ events: AuditEntry[]; total: number }>("/api/v1/audit-trail");
  return data.events ?? [];
}

export async function fetchSecurityStatus(): Promise<SecurityStatus> {
  const { data } = await api.get("/api/v1/security/status");
  return data;
}
