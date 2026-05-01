import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { HelmetProvider, Helmet } from "react-helmet-async";
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
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Search from "./pages/Search";
import StudentHome from "./pages/StudentHome";
import Reels from "./pages/Reels";
import Learning from "./pages/Learning";
import Insights from "./pages/Insights";
import CRM from "./pages/CRM";
import CreatorStorefront from "./pages/CreatorStorefront";
import Wallet from "./pages/Wallet";
import Billing from "./pages/Billing";
import Community from "./pages/Community";
import GroupChat from "./pages/GroupChat";

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

const CreatorOnly = ({ children }) => {
    const { user, loading } = useAuth();
    if (loading)
        return (
            <div className="grid min-h-screen place-items-center text-muted-foreground">
                Loading…
            </div>
        );
    if (!user) return <Navigate to="/login" replace />;
    if (user.role !== "creator" && user.role !== "admin") {
        return <Navigate to="/home" replace />;
    }
    return children;
};

const Shell = ({ children }) => <Layout>{children}</Layout>;

const HomeRoute = () => {
    const { user } = useAuth();
    const isCreator = user?.role === "creator" || user?.role === "admin";
    return isCreator ? (
        <Shell>
            <Feed />
        </Shell>
    ) : (
        <Shell>
            <StudentHome />
        </Shell>
    );
};

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
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password/:token" element={<ResetPassword />} />

            {/* Role-aware home */}
            <Route path="/home" element={<HomeRoute />} />
            <Route path="/feed" element={<Shell><Feed /></Shell>} />
            <Route path="/reels" element={<Shell><Reels /></Shell>} />
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
            <Route path="/c/:username" element={<Shell><CreatorStorefront /></Shell>} />
            <Route path="/p/:postId" element={<Shell><PostDetail /></Shell>} />
            <Route path="/leaderboard" element={<Shell><Leaderboard /></Shell>} />
            <Route path="/search" element={<Shell><Search /></Shell>} />
            <Route
                path="/learning"
                element={
                    <Protected>
                        <Shell><Learning /></Shell>
                    </Protected>
                }
            />
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
                    <CreatorOnly>
                        <Shell><Dashboard /></Shell>
                    </CreatorOnly>
                }
            />
            <Route
                path="/insights"
                element={
                    <CreatorOnly>
                        <Shell><Insights /></Shell>
                    </CreatorOnly>
                }
            />
            <Route
                path="/crm"
                element={
                    <CreatorOnly>
                        <Shell><CRM /></Shell>
                    </CreatorOnly>
                }
            />
            <Route
                path="/wallet"
                element={
                    <Protected>
                        <Shell><Wallet /></Shell>
                    </Protected>
                }
            />
            <Route
                path="/billing"
                element={
                    <Protected>
                        <Shell><Billing /></Shell>
                    </Protected>
                }
            />
            <Route
                path="/community"
                element={
                    <Protected>
                        <Shell><Community /></Shell>
                    </Protected>
                }
            />
            <Route
                path="/community/:groupId"
                element={
                    <Protected>
                        <Shell><GroupChat /></Shell>
                    </Protected>
                }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}

export default function App() {
    return (
        <HelmetProvider>
            <ThemeProvider>
                <AuthProvider>
                    <BrowserRouter>
                        <Helmet defaultTitle="Skiller — India's learn-to-earn network" titleTemplate="%s · Skiller">
                            <meta name="description" content="Skiller is India's learn-to-earn social network. Watch reels, take courses, post gigs, build your CRM, run ads, and earn skill tokens. Built for creators and learners." />
                            <link rel="canonical" href={typeof window !== "undefined" ? window.location.href : "https://skiller.app"} />
                            <meta property="og:site_name" content="Skiller" />
                            <meta property="og:type" content="website" />
                            <meta property="og:title" content="Skiller — Learn. Ship. Get paid." />
                            <meta property="og:description" content="India's learn-to-earn social network. Reels, courses, gigs, AI recommendations, skill tokens." />
                            <meta property="og:image" content="https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80" />
                            <meta name="twitter:card" content="summary_large_image" />
                            <meta name="twitter:title" content="Skiller — Learn. Ship. Get paid." />
                            <meta name="twitter:description" content="India's learn-to-earn social network." />
                            <meta name="twitter:image" content="https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80" />
                            <meta name="theme-color" content="#B91C1C" />
                            <meta name="robots" content="index,follow" />
                        </Helmet>
                        <AppRoutes />
                        <Toaster position="top-center" richColors />
                    </BrowserRouter>
                </AuthProvider>
            </ThemeProvider>
        </HelmetProvider>
    );
}
