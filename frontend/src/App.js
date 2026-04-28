import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import "./App.css";

import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";

import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Feed from "./pages/Feed";
import Explore from "./pages/Explore";
import UploadPage from "./pages/Upload";
import Profile from "./pages/Profile";
import Courses from "./pages/Courses";
import Gigs from "./pages/Gigs";
import PostDetail from "./pages/PostDetail";
import NotificationsPage from "./pages/Notifications";
import Dashboard from "./pages/Dashboard";
import Leaderboard from "./pages/Leaderboard";

const Protected = ({ children }) => {
    const { user, loading } = useAuth();
    if (loading)
        return (
            <div className="grid min-h-screen place-items-center text-muted-foreground">
                Loading…
            </div>
        );
    if (!user) return <Navigate to="/login" replace />;
    return children;
};

const Shell = ({ children }) => <Layout>{children}</Layout>;

function AppRoutes() {
    const { loading } = useAuth();
    if (loading)
        return (
            <div className="grid min-h-screen place-items-center text-muted-foreground">
                Loading…
            </div>
        );
    return (
        <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/feed" element={<Shell><Feed /></Shell>} />
            <Route path="/explore" element={<Shell><Explore /></Shell>} />
            <Route
                path="/upload"
                element={
                    <Protected>
                        <Shell><UploadPage /></Shell>
                    </Protected>
                }
            />
            <Route path="/courses" element={<Shell><Courses /></Shell>} />
            <Route path="/gigs" element={<Shell><Gigs /></Shell>} />
            <Route path="/u/:username" element={<Shell><Profile /></Shell>} />
            <Route path="/p/:postId" element={<Shell><PostDetail /></Shell>} />
            <Route path="/leaderboard" element={<Shell><Leaderboard /></Shell>} />
            <Route
                path="/notifications"
                element={
                    <Protected>
                        <Shell><NotificationsPage /></Shell>
                    </Protected>
                }
            />
            <Route
                path="/dashboard"
                element={
                    <Protected>
                        <Shell><Dashboard /></Shell>
                    </Protected>
                }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}

export default function App() {
    return (
        <ThemeProvider>
            <AuthProvider>
                <BrowserRouter>
                    <AppRoutes />
                    <Toaster position="top-center" richColors />
                </BrowserRouter>
            </AuthProvider>
        </ThemeProvider>
    );
}
