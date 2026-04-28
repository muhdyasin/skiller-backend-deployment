import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { formatApiError } from "../lib/api";
import ThemeToggle from "../components/ThemeToggle";

export default function Login() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const user = await login(email, password);
            toast.success("Welcome back!");
            navigate(user?.role === "creator" || user?.role === "admin" ? "/feed" : "/home");
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail) || "Login failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="grid min-h-screen grid-cols-1 md:grid-cols-2" data-testid="login-page">
            <div className="relative hidden md:block">
                <img
                    src="https://images.unsplash.com/photo-1519408469771-2586093c3f14?w=1200&q=80"
                    alt=""
                    className="absolute inset-0 h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-tr from-black/80 via-black/30 to-transparent" />
                <div className="absolute inset-0 flex flex-col justify-between p-10 text-white">
                    <Logo />
                    <div>
                        <div className="font-display text-4xl font-black leading-tight">
                            Welcome back.
                            <br />
                            Keep building.
                        </div>
                        <p className="mt-2 max-w-sm text-sm text-white/70">
                            Sign in to pick up where you left off — your feed, courses and gigs.
                        </p>
                    </div>
                </div>
            </div>

            <div className="relative flex flex-col items-center justify-center px-6 py-12">
                <div className="absolute right-6 top-6">
                    <ThemeToggle />
                </div>
                <div className="w-full max-w-sm">
                    <div className="mb-8 md:hidden">
                        <Logo />
                    </div>
                    <h1 className="font-display text-3xl font-bold tracking-tight">Sign in</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        New to Skiller?{" "}
                        <Link to="/register" className="font-semibold text-primary hover:underline" data-testid="to-register-link">
                            Create an account
                        </Link>
                    </p>

                    <form onSubmit={submit} className="mt-8 space-y-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@skiller.app"
                                data-testid="login-email-input"
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                data-testid="login-password-input"
                                className="rounded-xl"
                            />
                        </div>
                        <Button
                            type="submit"
                            disabled={loading}
                            className="h-11 w-full rounded-full"
                            data-testid="login-submit-btn"
                        >
                            {loading ? "Signing in…" : "Sign in"}
                        </Button>
                    </form>

                    <div className="mt-3 text-center text-sm">
                        <Link
                            to="/forgot-password"
                            className="text-muted-foreground hover:text-primary hover:underline"
                            data-testid="forgot-password-link"
                        >
                            Forgot password?
                        </Link>
                    </div>

                    <div className="mt-6 rounded-xl border border-dashed border-border p-4 text-xs text-muted-foreground">
                        <div className="mb-1 font-semibold text-foreground">Try a demo account</div>
                        Email: <span className="font-mono">maya@skiller.app</span>
                        <br />
                        Password: <span className="font-mono">Demo@123</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
