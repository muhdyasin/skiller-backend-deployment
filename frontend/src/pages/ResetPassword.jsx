import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, formatApiError } from "../lib/api";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import ThemeToggle from "../components/ThemeToggle";

export default function ResetPassword() {
    const { token } = useParams();
    const navigate = useNavigate();
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        if (password !== confirm) {
            toast.error("Passwords do not match");
            return;
        }
        setLoading(true);
        try {
            await api.post("/auth/reset-password", { token, new_password: password });
            toast.success("Password updated. Sign in to continue.");
            navigate("/login");
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail) || "Failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="relative grid min-h-screen place-items-center px-6" data-testid="reset-password-page">
            <div className="absolute right-6 top-6">
                <ThemeToggle />
            </div>
            <div className="w-full max-w-sm">
                <div className="mb-8">
                    <Logo />
                </div>
                <h1 className="font-display text-3xl font-bold tracking-tight">
                    Choose a new password
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    The link is valid for 60 minutes.
                </p>

                <form onSubmit={submit} className="mt-8 space-y-4">
                    <div className="space-y-1.5">
                        <Label htmlFor="pw">New password</Label>
                        <Input
                            id="pw"
                            type="password"
                            required
                            minLength={6}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            data-testid="reset-pw-input"
                            className="rounded-xl"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="pwc">Confirm password</Label>
                        <Input
                            id="pwc"
                            type="password"
                            required
                            minLength={6}
                            value={confirm}
                            onChange={(e) => setConfirm(e.target.value)}
                            data-testid="reset-pwc-input"
                            className="rounded-xl"
                        />
                    </div>
                    <Button
                        type="submit"
                        disabled={loading}
                        className="h-11 w-full rounded-full"
                        data-testid="reset-submit-btn"
                    >
                        {loading ? "Updating…" : "Update password"}
                    </Button>
                    <div className="text-center text-sm text-muted-foreground">
                        <Link to="/login" className="hover:underline">
                            Back to sign in
                        </Link>
                    </div>
                </form>
            </div>
        </div>
    );
}
