import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import apiClient from "../api/client";

const AuthContext = createContext(null);

function decodeToken(token) {
  if (!token) return null;
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(normalized));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() =>
    localStorage.getItem("access_token")
  );
  // `profile` comes from GET /auth/me. The JWT carries only `sub` and `exp`
  // by design, so the real name and role must be fetched, never guessed.
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);

  const login = useCallback((newToken) => {
    localStorage.setItem("access_token", newToken);
    setToken(newToken);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    setToken(null);
    setProfile(null);
  }, []);

  /**
   * Re-fetch the profile. Exposed so the Profile page can refresh the navbar
   * and sidebar immediately after a successful edit, instead of the UI
   * showing a stale name until the next reload.
   */
  const refreshProfile = useCallback(async () => {
    if (!localStorage.getItem("access_token")) return null;

    setProfileLoading(true);
    try {
      const response = await apiClient.get("/auth/me");
      setProfile(response.data);
      return response.data;
    } catch {
      return null;
    } finally {
      setProfileLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!token) {
      setProfile(null);
      return;
    }

    let cancelled = false;
    setProfileLoading(true);

    apiClient
      .get("/auth/me")
      .then((response) => {
        if (!cancelled) setProfile(response.data);
      })
      .catch(() => {
        // The 401 interceptor already handles an invalid token; anything
        // else (e.g. backend down) shouldn't wipe the session.
        if (!cancelled) setProfile(null);
      })
      .finally(() => {
        if (!cancelled) setProfileLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  // Keep tabs in sync, and react to the interceptor's 401 event.
  useEffect(() => {
    const handleStorage = (event) => {
      if (event.key === "access_token") setToken(event.newValue);
    };
    const handleUnauthorized = () => logout();

    window.addEventListener("storage", handleStorage);
    window.addEventListener("deepshield:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("deepshield:unauthorized", handleUnauthorized);
    };
  }, [logout]);

  const claims = useMemo(() => decodeToken(token), [token]);

  const user = useMemo(() => {
    if (profile) {
      return {
        id: profile.id,
        email: profile.email,
        fullName: profile.full_name,
        role: profile.role_name,
        isActive: profile.is_active,
        createdAt: profile.created_at,
      };
    }
    // Fall back to the token subject while /auth/me is in flight.
    if (claims?.sub) {
      return { email: claims.sub, fullName: null, role: null };
    }
    return null;
  }, [profile, claims]);

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      user,
      profileLoading,
      isAdmin: profile?.role_name === "Admin",
      login,
      logout,
      refreshProfile,
    }),
    [token, user, profileLoading, profile, login, logout, refreshProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
