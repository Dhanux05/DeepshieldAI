import { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";
import { useLocation } from "react-router-dom";

const LayoutContext = createContext(null);

export function LayoutProvider({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  // Close the mobile drawer automatically on navigation.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const toggleMobile = useCallback(() => setMobileOpen((prev) => !prev), []);
  const closeMobile = useCallback(() => setMobileOpen(false), []);
  const toggleCollapsed = useCallback(() => setCollapsed((prev) => !prev), []);

  const value = useMemo(
    () => ({ mobileOpen, toggleMobile, closeMobile, collapsed, toggleCollapsed }),
    [mobileOpen, toggleMobile, closeMobile, collapsed, toggleCollapsed]
  );

  return <LayoutContext.Provider value={value}>{children}</LayoutContext.Provider>;
}

export function useLayout() {
  const context = useContext(LayoutContext);
  if (context === null) {
    throw new Error("useLayout must be used within LayoutProvider");
  }
  return context;
}
