import { useRef, useState } from "react";
import { Mic, Square, Trash2, Send, Play, Pause } from "lucide-react";

export default function VoiceRecorder({ onSend, disabled }) {
    const [state, setState] = useState("idle"); // idle | recording | preview
    const [elapsed, setElapsed] = useState(0);
    const [blob, setBlob] = useState(null);
    const [blobUrl, setBlobUrl] = useState(null);
    const [playing, setPlaying] = useState(false);
    const recorderRef = useRef(null);
    const chunksRef = useRef([]);
    const timerRef = useRef(null);
    const audioRef = useRef(null);
    const startedAt = useRef(0);

    const start = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus"
                : "audio/webm";
            const r = new MediaRecorder(stream, { mimeType: mime });
            chunksRef.current = [];
            r.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
            r.onstop = () => {
                const b = new Blob(chunksRef.current, { type: mime });
                setBlob(b);
                setBlobUrl(URL.createObjectURL(b));
                setState("preview");
                stream.getTracks().forEach((t) => t.stop());
            };
            r.start();
            recorderRef.current = r;
            startedAt.current = Date.now();
            setState("recording");
            setElapsed(0);
            timerRef.current = setInterval(() => {
                const secs = Math.floor((Date.now() - startedAt.current) / 1000);
                setElapsed(secs);
                if (secs >= 120) stop(); // 2-min cap
            }, 200);
        } catch (e) {
            alert("Microphone permission denied or unavailable.");
        }
    };

    const stop = () => {
        clearInterval(timerRef.current);
        const r = recorderRef.current;
        if (r && r.state !== "inactive") r.stop();
    };

    const discard = () => {
        if (blobUrl) URL.revokeObjectURL(blobUrl);
        setBlob(null);
        setBlobUrl(null);
        setState("idle");
        setElapsed(0);
    };

    const send = async () => {
        if (!blob) return;
        const durMs = elapsed * 1000;
        const file = new File([blob], `voice-${Date.now()}.webm`, { type: blob.type });
        await onSend(file, durMs);
        discard();
    };

    const togglePlay = () => {
        const a = audioRef.current;
        if (!a) return;
        if (a.paused) {
            a.play();
            setPlaying(true);
        } else {
            a.pause();
            setPlaying(false);
        }
    };

    if (state === "idle") {
        return (
            <button
                type="button"
                onClick={start}
                disabled={disabled}
                className="grid h-10 w-10 shrink-0 place-items-center rounded-full hover:bg-accent disabled:opacity-50"
                aria-label="Record voice note"
                data-testid="chat-mic-btn"
            >
                <Mic size={18} />
            </button>
        );
    }

    if (state === "recording") {
        return (
            <div
                className="flex h-10 flex-1 items-center gap-2 rounded-full border border-primary/30 bg-primary/5 px-3"
                data-testid="chat-voice-recording"
            >
                <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                <span className="text-xs font-semibold tabular-nums">
                    {`${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`}
                </span>
                <div className="ml-2 flex-1 text-[11px] text-muted-foreground">Recording…</div>
                <button
                    type="button"
                    onClick={discard}
                    className="grid h-8 w-8 place-items-center rounded-full text-muted-foreground hover:bg-accent"
                    aria-label="Cancel"
                    data-testid="chat-voice-cancel"
                >
                    <Trash2 size={14} />
                </button>
                <button
                    type="button"
                    onClick={stop}
                    className="grid h-8 w-8 place-items-center rounded-full bg-primary text-primary-foreground"
                    aria-label="Stop"
                    data-testid="chat-voice-stop"
                >
                    <Square size={14} />
                </button>
            </div>
        );
    }

    // preview
    return (
        <div
            className="flex h-10 flex-1 items-center gap-2 rounded-full border border-border bg-secondary/50 px-3"
            data-testid="chat-voice-preview"
        >
            <button
                type="button"
                onClick={togglePlay}
                className="grid h-8 w-8 place-items-center rounded-full bg-primary text-primary-foreground"
                aria-label={playing ? "Pause" : "Play"}
            >
                {playing ? <Pause size={14} /> : <Play size={14} />}
            </button>
            <audio
                ref={audioRef}
                src={blobUrl}
                onEnded={() => setPlaying(false)}
                className="hidden"
            />
            <span className="text-xs font-semibold tabular-nums">
                {`${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`}
            </span>
            <div className="ml-1 flex-1 text-[11px] text-muted-foreground">Voice note ready</div>
            <button
                type="button"
                onClick={discard}
                className="grid h-8 w-8 place-items-center rounded-full text-muted-foreground hover:bg-accent"
                aria-label="Discard"
                data-testid="chat-voice-discard"
            >
                <Trash2 size={14} />
            </button>
            <button
                type="button"
                onClick={send}
                className="grid h-8 w-8 place-items-center rounded-full bg-primary text-primary-foreground"
                aria-label="Send"
                data-testid="chat-voice-send"
            >
                <Send size={14} />
            </button>
        </div>
    );
}
