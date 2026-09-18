"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { User } from "@/types";
import { api } from "@/lib/api-client";
import { useRouter } from "next/navigation";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (data: any) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => void;
  refetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const fetchUser = async () => {
    const token = typeof window !== "undefined" ? localStorage.getItem("restoops_access_token") : null;
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const userData = await api.get<User>("/auth/me");
      setUser(userData);
    } catch (err) {
      setUser(null);
      api.clearTokens();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const login = async (credentials: any) => {
    setIsLoading(true);
    try {
      const data = await api.post<{ access_token: string; refresh_token: string }>("/auth/login", credentials);
      api.setTokens(data.access_token, data.refresh_token);
      await fetchUser();
      router.push("/dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: any) => {
    setIsLoading(true);
    try {
      await api.post("/auth/register", payload);
      await login({ email: payload.email, password: payload.password });
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.clearTokens();
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refetchUser: fetchUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
