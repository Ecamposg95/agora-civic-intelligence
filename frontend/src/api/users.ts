import { apiClient } from "./client";
import type { Paginated, User } from "@/types/auth";
import type {
  ListUsersParams,
  PasswordResetResult,
  UserCreatePayload,
  UserCreatedResponse,
  UserUpdatePayload,
} from "@/types/users";

export async function listUsers(
  params: ListUsersParams,
): Promise<Paginated<User>> {
  // Drop empty/undefined params so the API receives a clean query.
  const clean: Record<string, unknown> = {};
  Object.entries(params).forEach(([k, v]) => {
    if (v !== "" && v !== undefined && v !== null) clean[k] = v;
  });
  const { data } = await apiClient.get<Paginated<User>>("/users", { params: clean });
  return data;
}

export async function createUser(
  payload: UserCreatePayload,
): Promise<UserCreatedResponse> {
  const { data } = await apiClient.post<UserCreatedResponse>("/users", payload);
  return data;
}

export async function updateUser(
  id: string,
  payload: UserUpdatePayload,
): Promise<User> {
  const { data } = await apiClient.patch<User>(`/users/${id}`, payload);
  return data;
}

export async function deleteUser(id: string): Promise<void> {
  await apiClient.delete(`/users/${id}`);
}

export async function restoreUser(id: string): Promise<User> {
  const { data } = await apiClient.post<User>(`/users/${id}/restore`);
  return data;
}

export async function setActive(id: string, active: boolean): Promise<User> {
  const action = active ? "activate" : "deactivate";
  const { data } = await apiClient.post<User>(`/users/${id}/${action}`);
  return data;
}

export async function resetPassword(id: string): Promise<PasswordResetResult> {
  const { data } = await apiClient.post<PasswordResetResult>(
    `/users/${id}/reset-password`,
  );
  return data;
}

export async function updateMe(payload: {
  full_name?: string;
  phone?: string | null;
}): Promise<User> {
  const { data } = await apiClient.patch<User>("/users/me", payload);
  return data;
}

export async function changeMyPassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await apiClient.post("/users/me/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}
