import { useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "../lib/api";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import ThemeToggle from "../components/ThemeToggle";

export default function ForgotPassword() {
    const [email, setEmail] = useState("");
    const [done, setDone] = useState(false);
    const [loading, setLoading] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post("/auth/forgot-password", { email });
            setDone(true);
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail) || "Failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="relative grid min-h-screen place-items-center px-6" data-testid="forgot-password-page">
            <div className="absolute right-6 top-6">
                <ThemeToggle />
            </div>
            <div className="w-full max-w-sm">
                <div className="mb-8">
                    <Logo />
                </div>
                <h1 className="font-display text-3xl font-bold tracking-tight">
                    Reset your password
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Enter your email and we'll send a reset link.
                </p>

                {done ? (
                    <div className="mt-8 rounded-2xl border border-border p-4 text-sm">
                        If that email exists, a reset link has been sent. Check your inbox (and your backend logs in dev mode).
                        <div className="mt-4">
                            <Link to="/login" className="font-semibold text-primary hover:underline">
                                Back to sign in
                            </Link>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={submit} className="mt-8 space-y-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                data-testid="forgot-email-input"
                                className="rounded-xl"
                            />
                        </div>
                        <Button
                            type="submit"
                            disabled={loading}
                            className="h-11 w-full rounded-full"
                            data-testid="forgot-submit-btn"
                        >
                            {loading ? "Sending…" : "Send reset link"}
                        </Button>
                        <div className="text-center text-sm text-muted-foreground">
                            <Link to="/login" className="hover:underline">
                                Back to sign in
                            </Link>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
