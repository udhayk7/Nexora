"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  apiClient,
  setAccessToken,
  TokenResponse,
  UserProfile,
} from "@/lib/api";

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchProfile = useCallback(async (): Promise<UserProfile | null> => {
    try {
      const profile = await apiClient<UserProfile>("/api/v1/users/me");
      setUser(profile);
      return profile;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  // Initialize session via HttpOnly refresh cookie on page load
  useEffect(() => {
    let mounted = true;

    async function initSession() {
      try {
        const tokenRes = await apiClient<TokenResponse>("/api/v1/auth/refresh", {
          method: "POST",
          body: JSON.stringify({}),
        });
        setAccessToken(tokenRes.access_token);
        if (mounted) {
          await fetchProfile();
        }
      } catch {
        setAccessToken(null);
        if (mounted) {
          setUser(null);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    initSession();

    return () => {
      mounted = false;
    };
  }, [fetchProfile]);

  const login = async (email: string, password: string): Promise<void> => {
    const tokenRes = await apiClient<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    setAccessToken(tokenRes.access_token);
    await fetchProfile();
  };

  const register = async (
    email: string,
    password: string,
    fullName: string
  ): Promise<void> => {
    const tokenRes = await apiClient<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
      }),
    });

    setAccessToken(tokenRes.access_token);
    await fetchProfile();
  };

  const logout = async (): Promise<void> => {
    try {
      await apiClient("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({}),
      });
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

