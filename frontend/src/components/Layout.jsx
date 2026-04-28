import { NavLink, useNavigate } from "react-router-dom";
import {
    Home,
    Compass,
    PlusSquare,
    Briefcase,
    BookOpen,
    User as UserIcon,
    Sun,
    Moon,
    LogOut,
    LayoutDashboard,
    Trophy,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { Logo } from "./Logo";
import { Button } from "./ui/button";
import NotificationsBell from "./NotificationsBell";
import XPBadge from "./XPBadge";

const navItems = [
    { to: "/feed", label: "Home", icon: Home, tid: "nav-home" },
    { to: "/explore", label: "Explore", icon: Compass, tid: "nav-explore" },
    { to: "/upload", label: "Upload", icon: PlusSquare, tid: "nav-upload" },
    { to: "/courses", label: "Courses", icon: BookOpen, tid: "nav-courses" },
    { to: "/gigs", label: "Gigs", icon: Briefcase, tid: "nav-gigs" },
];

const moreNav = [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, tid: "nav-dashboard", auth: true },
    { to: "/leaderboard", label: "Leaderboard", icon: Trophy, tid: "nav-leaderboard" },
];

export default function Layout({ children }) {
    const { user, logout } = useAuth();
    const { theme, toggle } = useTheme();
    const navigate = useNavigate();

    const profilePath = user ? `/u/${user.username}` : "/login";

    return (
        <div className="min-h-screen bg-background text-foreground">
            {/* Desktop sidebar */}
            <aside
                className="fixed left-0 top-0 z-40 hidden h-screen w-64 flex-col border-r border-border bg-background p-5 md:flex"
                data-testid="sidebar"
            >
                <div className="mb-8">
                    <Logo />
                </div>
                <nav className="flex flex-1 flex-col gap-0.5">
                    {navItems.map(({ to, label, icon: Icon, tid }) => (
                        <NavLink
                            key={to}
                            to={to}
                            data-testid={tid}
                            className={({ isActive }) =>
                                `group flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-medium transition-colors ${
                                    isActive
                                        ? "bg-primary text-primary-foreground"
                                        : "text-foreground hover:bg-accent"
                                }`
                            }
                        >
                            <Icon size={18} />
                            <span>{label}</span>
                        </NavLink>
                    ))}
                    {moreNav
                        .filter((it) => !it.auth || user)
                        .map(({ to, label, icon: Icon, tid }) => (
                            <NavLink
                                key={to}
                                to={to}
                                data-testid={tid}
                                className={({ isActive }) =>
                                    `flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-medium transition-colors ${
                                        isActive
                                            ? "bg-primary text-primary-foreground"
                                            : "text-foreground hover:bg-accent"
                                    }`
                                }
                            >
                                <Icon size={18} />
                                <span>{label}</span>
                            </NavLink>
                        ))}
                    <NavLink
                        to={profilePath}
                        data-testid="nav-profile"
                        className={({ isActive }) =>
                            `flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-medium transition-colors ${
                                isActive
                                    ? "bg-primary text-primary-foreground"
                                    : "text-foreground hover:bg-accent"
                            }`
                        }
                    >
                        <UserIcon size={18} />
                        <span>Profile</span>
                    </NavLink>
                </nav>

                {user && (
                    <div className="mt-3">
                        <XPBadge user={user} />
                    </div>
                )}

                <div className="mt-3 space-y-1 border-t border-border pt-3">
                    <button
                        onClick={toggle}
                        data-testid="theme-toggle"
                        className="flex w-full items-center gap-3 rounded-full px-4 py-2.5 text-sm font-medium hover:bg-accent"
                    >
                        {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
                        <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
                    </button>
                    {user ? (
                        <button
                            onClick={() => {
                                logout();
                                navigate("/");
                            }}
                            data-testid="logout-btn"
                            className="flex w-full items-center gap-3 rounded-full px-4 py-2.5 text-sm font-medium text-destructive hover:bg-accent"
                        >
                            <LogOut size={16} />
                            <span>Log out</span>
                        </button>
                    ) : (
                        <Button
                            data-testid="sidebar-login-btn"
                            onClick={() => navigate("/login")}
                            className="w-full rounded-full"
                        >
                            Sign in
                        </Button>
                    )}
                </div>
            </aside>

            {/* Mobile top bar */}
            <header
                className="glass sticky top-0 z-30 flex items-center justify-between border-b border-border px-4 py-3 md:hidden"
                data-testid="mobile-topbar"
            >
                <Logo size="sm" />
                <div className="flex items-center gap-1">
                    {user && <XPBadge user={user} compact />}
                    <NotificationsBell />
                    <button
                        data-testid="theme-toggle-mobile"
                        onClick={toggle}
                        className="grid h-9 w-9 place-items-center rounded-full hover:bg-accent"
                    >
                        {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
                    </button>
                    {user ? (
                        <button
                            data-testid="mobile-logout-btn"
                            onClick={() => {
                                logout();
                                navigate("/");
                            }}
                            className="grid h-9 w-9 place-items-center rounded-full hover:bg-accent"
                        >
                            <LogOut size={18} />
                        </button>
                    ) : (
                        <Button
                            size="sm"
                            onClick={() => navigate("/login")}
                            className="rounded-full"
                            data-testid="mobile-login-btn"
                        >
                            Sign in
                        </Button>
                    )}
                </div>
            </header>

            {/* Desktop top right floating actions (notifications) */}
            <div className="fixed right-6 top-6 z-30 hidden md:block">
                <NotificationsBell />
            </div>

            {/* Main */}
            <main className="md:pl-64">
                <div className="min-h-screen pb-24 md:pb-8">{children}</div>
            </main>

            {/* Mobile bottom nav */}
            <nav
                className="glass fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around border-t border-border px-2 py-2 md:hidden"
                data-testid="bottom-nav"
            >
                {navItems.map(({ to, label, icon: Icon, tid }) => (
                    <NavLink
                        key={to}
                        to={to}
                        data-testid={`${tid}-mobile`}
                        className={({ isActive }) =>
                            `grid h-12 w-12 place-items-center rounded-full transition-colors ${
                                isActive ? "bg-primary text-primary-foreground" : "text-foreground"
                            }`
                        }
                        aria-label={label}
                    >
                        <Icon size={20} />
                    </NavLink>
                ))}
                <NavLink
                    to={profilePath}
                    data-testid="nav-profile-mobile"
                    className={({ isActive }) =>
                        `grid h-12 w-12 place-items-center rounded-full ${
                            isActive ? "bg-primary text-primary-foreground" : "text-foreground"
                        }`
                    }
                >
                    <UserIcon size={20} />
                </NavLink>
            </nav>
        </div>
    );
}
