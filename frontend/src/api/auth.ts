import { apiClient } from "./client";
import type { LoginRequest, TokenResponse, User } from "@/types/auth";

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
  return data;
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await apiClient.get<User>("/auth/me");
  return data;
}
