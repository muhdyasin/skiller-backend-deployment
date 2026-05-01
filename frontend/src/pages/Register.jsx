import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { formatApiError } from "../lib/api";
import ThemeToggle from "../components/ThemeToggle";
import { GraduationCap, Briefcase, Gift } from "lucide-react";

export default function Register() {
    const { register } = useAuth();
    const navigate = useNavigate();
    const [params] = useSearchParams();
    const refFromUrl = (params.get("ref") || "").trim().toUpperCase();
    const [form, setForm] = useState({
        name: "",
        username: "",
        email: "",
        password: "",
        role: "student",
        referral_code: refFromUrl,
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (refFromUrl) {
            setForm((f) => ({ ...f, referral_code: refFromUrl }));
        }
    }, [refFromUrl]);

    const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

    const submit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const user = await register(form);
            toast.success("Welcome to Skiller!");
            navigate(user?.role === "creator" ? "/dashboard" : "/home");
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail) || "Sign up failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="grid min-h-screen grid-cols-1 md:grid-cols-2" data-testid="register-page">
            <div className="relative flex flex-col items-center justify-center px-6 py-12 order-2 md:order-1">
                <div className="absolute right-6 top-6">
                    <ThemeToggle />
                </div>
                <div className="w-full max-w-sm">
                    <div className="mb-8">
                        <Logo />
                    </div>
                    <h1 className="font-display text-3xl font-bold tracking-tight">
                        Create your account
                    </h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Already here?{" "}
                        <Link to="/login" className="font-semibold text-primary hover:underline" data-testid="to-login-link">
                            Sign in
                        </Link>
                    </p>

                    {/* Role selector */}
                    <div className="mt-6 grid grid-cols-2 gap-3" data-testid="role-selector">
                        <RoleCard
                            label="Student"
                            description="Learn skills, watch reels, take courses."
                            icon={GraduationCap}
                            active={form.role === "student"}
                            onClick={() => set("role", "student")}
                            tid="role-student"
                        />
                        <RoleCard
                            label="Creator / Institution"
                            description="Teach, post gigs, run ads, run a CRM."
                            icon={Briefcase}
                            active={form.role === "creator"}
                            onClick={() => set("role", "creator")}
                            tid="role-creator"
                        />
                    </div>

                    <form onSubmit={submit} className="mt-6 space-y-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="name">{form.role === "creator" ? "Brand or full name" : "Full name"}</Label>
                            <Input
                                id="name"
                                required
                                value={form.name}
                                onChange={(e) => set("name", e.target.value)}
                                placeholder="Priya Kapoor"
                                data-testid="register-name-input"
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="username">Username</Label>
                            <Input
                                id="username"
                                required
                                value={form.username}
                                onChange={(e) =>
                                    set(
                                        "username",
                                        e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "")
                                    )
                                }
                                placeholder="priya"
                                data-testid="register-username-input"
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                required
                                value={form.email}
                                onChange={(e) => set("email", e.target.value)}
                                placeholder="you@skiller.app"
                                data-testid="register-email-input"
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                required
                                minLength={6}
                                value={form.password}
                                onChange={(e) => set("password", e.target.value)}
                                placeholder="At least 6 characters"
                                data-testid="register-password-input"
                                className="rounded-xl"
                            />
                        </div>
                        <Button
                            type="submit"
                            disabled={loading}
                            className="h-11 w-full rounded-full"
                            data-testid="register-submit-btn"
                        >
                            {loading
                                ? "Creating account…"
                                : `Create ${form.role === "creator" ? "creator" : "student"} account`}
                        </Button>
                        {form.referral_code && (
                            <div
                                className="flex items-center gap-2 rounded-full border border-primary/30 bg-primary/5 px-3 py-2 text-xs text-primary"
                                data-testid="referral-banner"
                            >
                                <Gift size={14} />
                                Joining via referral code <strong>{form.referral_code}</strong> — your friend earns 500 tokens when you go premium.
                            </div>
                        )}
                    </form>
                </div>
            </div>

            <div className="relative hidden md:block order-1 md:order-2">
                <img
                    src="https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80"
                    alt=""
                    className="absolute inset-0 h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-tl from-black/80 via-black/30 to-transparent" />
                <div className="absolute inset-0 flex flex-col justify-end p-10 text-white">
                    <div className="font-display text-4xl font-black leading-tight">
                        Learn. Ship.
                        <br />
                        Get paid.
                    </div>
                    <p className="mt-2 max-w-sm text-sm text-white/70">
                        Join 100K+ creators turning their skills into income.
                    </p>
                </div>
            </div>
        </div>
    );
}

function RoleCard({ label, description, icon: Icon, active, onClick, tid }) {
    return (
        <button
            type="button"
            onClick={onClick}
            data-testid={tid}
            className={`flex flex-col items-start gap-2 rounded-2xl border p-3 text-left transition-all ${
                active
                    ? "border-primary bg-primary/5 ring-2 ring-primary"
                    : "border-border hover:border-primary/40"
            }`}
        >
            <Icon size={18} className={active ? "text-primary" : "text-muted-foreground"} />
            <div>
                <div className="text-sm font-semibold">{label}</div>
                <div className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                    {description}
                </div>
            </div>
        </button>
    );
}
