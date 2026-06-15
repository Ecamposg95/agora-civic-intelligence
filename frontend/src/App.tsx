import { JSX, Suspense, lazy, useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { useAuthStore } from "@/store/authStore";

// Route-level code splitting: heavy deps (MapLibre, Recharts) load only on the
// routes that need them, keeping the initial bundle small.
const LoginPage = lazy(() =>
  import("@/pages/LoginPage").then((m) => ({ default: m.LoginPage })),
);
const DashboardPage = lazy(() =>
  import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const MapExplorerPage = lazy(() =>
  import("@/pages/MapExplorerPage").then((m) => ({ default: m.MapExplorerPage })),
);
const AnalyticsPage = lazy(() =>
  import("@/pages/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })),
);
const UsersPage = lazy(() =>
  import("@/pages/UsersPage").then((m) => ({ default: m.UsersPage })),
);
const ProfilePage = lazy(() =>
  import("@/pages/ProfilePage").then((m) => ({ default: m.ProfilePage })),
);
const SourcesPage = lazy(() =>
  import("@/pages/SourcesPage").then((m) => ({ default: m.SourcesPage })),
);
const OrganizationSettingsPage = lazy(() =>
  import("@/pages/OrganizationSettingsPage").then((m) => ({
    default: m.OrganizationSettingsPage,
  })),
);
const ChangePasswordPage = lazy(() =>
  import("@/pages/ChangePasswordPage").then((m) => ({ default: m.ChangePasswordPage })),
);

function RequireAuth({ children }: { children: JSX.Element }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const loadCurrentUser = useAuthStore((s) => s.loadCurrentUser);

  useEffect(() => {
    if (isAuthenticated) void loadCurrentUser();
  }, [isAuthenticated, loadCurrentUser]);

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  // Forced password change gate (backend returns 428 on tenant endpoints).
  if (user?.must_change_password) return <Navigate to="/change-password" replace />;
  return children;
}

function RequireSession({ children }: { children: JSX.Element }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const loadCurrentUser = useAuthStore((s) => s.loadCurrentUser);

  useEffect(() => {
    if (isAuthenticated) void loadCurrentUser();
  }, [isAuthenticated, loadCurrentUser]);

  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function RouteFallback() {
  return (
    <div className="grid h-screen place-items-center bg-bg text-ink-faint">
      Loading…
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/change-password"
            element={
              <RequireSession>
                <ChangePasswordPage />
              </RequireSession>
            }
          />
          <Route
            path="/"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />
          <Route
            path="/maps"
            element={
              <RequireAuth>
                <MapExplorerPage />
              </RequireAuth>
            }
          />
          <Route
            path="/analytics"
            element={
              <RequireAuth>
                <AnalyticsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/users"
            element={
              <RequireAuth>
                <UsersPage />
              </RequireAuth>
            }
          />
          <Route
            path="/sources"
            element={
              <RequireAuth>
                <SourcesPage />
              </RequireAuth>
            }
          />
          <Route
            path="/organization"
            element={
              <RequireAuth>
                <OrganizationSettingsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/profile"
            element={
              <RequireAuth>
                <ProfilePage />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
