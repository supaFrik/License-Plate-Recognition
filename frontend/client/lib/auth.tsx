import {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  apiFetch,
  AuthUser,
  clearAccessToken,
  readApiError,
  setAccessToken,
  TokenResponse,
} from "@/lib/api";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: AuthUser | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: (silent?: boolean) => Promise<boolean>;
  authFetch: (
    path: string,
    init?: RequestInit,
    retry?: boolean,
  ) => Promise<Response>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function parseTokenResponse(response: Response) {
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }

  return (await response.json()) as TokenResponse;
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const applyAuthPayload = useCallback((payload: TokenResponse) => {
    setAccessToken(payload.access_token);
    setUser(payload.user);
    setStatus("authenticated");
  }, []);

  const clearSession = useCallback(() => {
    clearAccessToken();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const refreshSession = useCallback(
    async (silent = true) => {
      try {
        const response = await apiFetch("/auth/refresh", { method: "POST" });
        const payload = await parseTokenResponse(response);
        applyAuthPayload(payload);
        return true;
      } catch (error) {
        clearSession();
        if (!silent) {
          throw error;
        }
        return false;
      }
    },
    [applyAuthPayload, clearSession],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await apiFetch("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });
      const payload = await parseTokenResponse(response);
      applyAuthPayload(payload);
    },
    [applyAuthPayload],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      const response = await apiFetch("/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });
      const payload = await parseTokenResponse(response);
      applyAuthPayload(payload);
    },
    [applyAuthPayload],
  );

  const logout = useCallback(async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const authFetch = useCallback(
    async (path: string, init: RequestInit = {}, retry = true) => {
      let response = await apiFetch(path, init);
      if (response.status === 401 && retry) {
        const refreshed = await refreshSession(true);
        if (refreshed) {
          response = await apiFetch(path, init);
        }
      }
      if (response.status === 401) {
        clearSession();
      }
      return response;
    },
    [clearSession, refreshSession],
  );

  useEffect(() => {
    let isMounted = true;

    (async () => {
      const refreshed = await refreshSession(true);
      if (!isMounted) {
        return;
      }
      if (!refreshed) {
        setStatus("unauthenticated");
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [refreshSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      login,
      register,
      logout,
      refreshSession,
      authFetch,
    }),
    [authFetch, login, logout, refreshSession, register, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
