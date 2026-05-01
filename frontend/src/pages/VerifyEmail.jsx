import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { CheckCircle2, XCircle } from "lucide-react";
import { api, formatApiError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";

export default function VerifyEmail() {
    const { token } = useParams();
    const navigate = useNavigate();
    const { refresh, user } = useAuth();
    const [state, setState] = useState("loading"); // loading | success | error
    const [message, setMessage] = useState("");
    const sentRef = useRef(false);

    useEffect(() => {
        // Single-shot guard — StrictMode would otherwise fire this twice in dev,
        // and the second call would hit a now-used token and flip to error.
        if (sentRef.current) return;
        sentRef.current = true;
        (async () => {
            try {
                await api.post("/auth/verify-email", { token });
                setState("success");
                setMessage("Your email is verified. +25 XP unlocked!");
                if (user) await refresh();
            } catch (err) {
                // If the user is already verified (e.g. retrying a used link),
                // treat as success instead of error.
                try {
                    const me = await api.get("/auth/me");
                    if (me.data?.email_verified) {
                        setState("success");
                        setMessage("Your email is verified. +25 XP unlocked!");
                        await refresh();
                        return;
                    }
                } catch {
                    /* ignore */
                }
                setState("error");
                setMessage(
                    formatApiError(err.response?.data?.detail) ||
                        "Verification link is invalid or expired.",
                );
            }
        })();
    }, [token]); // eslint-disable-line

    return (
        <div
            className="grid min-h-screen place-items-center bg-background px-6 py-12"
            data-testid="verify-email-page"
        >
            <Helmet>
                <title>Verify email</title>
            </Helmet>
            <div className="w-full max-w-md rounded-3xl border border-border bg-card p-8 text-center">
                {state === "loading" && (
                    <>
                        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        <h1 className="mt-4 font-display text-2xl font-bold">Verifying…</h1>
                    </>
                )}
                {state === "success" && (
                    <>
                        <CheckCircle2 size={44} className="mx-auto text-emerald-500" />
                        <h1 className="mt-4 font-display text-2xl font-bold" data-testid="verify-success">
                            You're verified!
                        </h1>
                        <p className="mt-2 text-sm text-muted-foreground">{message}</p>
                        <Button
                            onClick={() => navigate(user ? "/home" : "/login")}
                            className="mt-6 w-full rounded-full"
                            data-testid="verify-continue-btn"
                        >
                            Continue to Skiller
                        </Button>
                    </>
                )}
                {state === "error" && (
                    <>
                        <XCircle size={44} className="mx-auto text-rose-500" />
                        <h1 className="mt-4 font-display text-2xl font-bold" data-testid="verify-error">
                            Could not verify
                        </h1>
                        <p className="mt-2 text-sm text-muted-foreground">{message}</p>
                        <Button
                            onClick={() => navigate(user ? "/home" : "/login")}
                            variant="outline"
                            className="mt-6 w-full rounded-full"
                        >
                            Go back
                        </Button>
                    </>
                )}
            </div>
        </div>
    );
}
