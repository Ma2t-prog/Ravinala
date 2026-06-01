import { useMutation, useQuery } from "@tanstack/react-query";
import {
  deleteUser,
  fetchAuditTrail,
  fetchRoles,
  fetchSecurityStatus,
  fetchUser,
  fetchUsers,
  updateUser,
  type UpdateUserRequest,
} from "../api/users";

export const usersKeys = {
  all: ["users"] as const,
  list: () => ["users", "list"] as const,
  detail: (id: string) => ["users", id] as const,
  roles: () => ["users", "roles"] as const,
  audit: () => ["users", "audit"] as const,
  security: () => ["users", "security"] as const,
};

export function useUsers() {
  return useQuery({
    queryKey: usersKeys.list(),
    queryFn: fetchUsers,
    staleTime: 30_000,
  });
}

export function useUser(userId: string) {
  return useQuery({
    queryKey: usersKeys.detail(userId),
    queryFn: () => fetchUser(userId),
    enabled: userId.length > 0,
    staleTime: 30_000,
  });
}

export function useRoles() {
  return useQuery({
    queryKey: usersKeys.roles(),
    queryFn: fetchRoles,
    staleTime: 60 * 60_000,
  });
}

export function useAuditTrail() {
  return useQuery({
    queryKey: usersKeys.audit(),
    queryFn: fetchAuditTrail,
    staleTime: 30_000,
  });
}

export function useSecurityStatus() {
  return useQuery({
    queryKey: usersKeys.security(),
    queryFn: fetchSecurityStatus,
    staleTime: 60_000,
  });
}

export function useUpdateUser() {
  return useMutation({
    mutationFn: ({
      userId,
      update,
    }: {
      userId: string;
      update: UpdateUserRequest;
    }) => updateUser(userId, update),
  });
}

export function useDeleteUser() {
  return useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
  });
}
