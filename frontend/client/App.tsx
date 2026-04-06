import "./global.css";

import { AuthProvider, useAuth } from "@/lib/auth";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

import History from "./pages/History";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import RecognitionConsole from "./pages/RecognitionConsole";
import Signup from "./pages/Signup";
import Vehicles from "./pages/Vehicles";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
});

function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card px-8 py-10 shadow-2xl shadow-black/20">
        <div className="mb-4 h-2 w-24 rounded-full bg-primary/70" />
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          VietPlateAI
        </h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Establishing a secure operator session.
        </p>
      </div>
    </div>
  );
}

function RootRedirect() {
  const { status } = useAuth();

  if (status === "loading") {
    return <LoadingScreen />;
  }

  return (
    <Navigate
      replace
      to={status === "authenticated" ? "/console" : "/login"}
    />
  );
}

function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <LoadingScreen />;
  }

  if (status !== "authenticated") {
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  return <Outlet />;
}

function GuestOnlyRoute() {
  const { status } = useAuth();

  if (status === "loading") {
    return <LoadingScreen />;
  }

  if (status === "authenticated") {
    return <Navigate replace to="/console" />;
  }

  return <Outlet />;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route element={<GuestOnlyRoute />}>
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
            </Route>
            <Route element={<ProtectedRoute />}>
              <Route path="/console" element={<RecognitionConsole />} />
              <Route path="/vehicles" element={<Vehicles />} />
              <Route path="/history" element={<History />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

const container = document.getElementById("root");

if (container) {
  createRoot(container).render(<App />);
}
