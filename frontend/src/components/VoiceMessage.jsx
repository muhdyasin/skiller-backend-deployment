import { useRef, useState } from "react";
import { Play, Pause } from "lucide-react";
import { fileSrc } from "../lib/upload";

export default function VoiceMessage({ src, durationMs, mine }) {
    const audioRef = useRef(null);
    const [playing, setPlaying] = useState(false);
    const [progress, setProgress] = useState(0);

    const toggle = () => {
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

    const onTime = () => {
        const a = audioRef.current;
        if (!a || !a.duration) return;
        setProgress(a.currentTime / a.duration);
    };

    const total = Math.max(1, Math.floor((durationMs || 0) / 1000));
    const mins = Math.floor(total / 60);
    const secs = total % 60;

    return (
        <div className="flex items-center gap-2 py-0.5" data-testid="voice-message">
            <button
                type="button"
                onClick={toggle}
                className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${
                    mine
                        ? "bg-primary-foreground/20 text-primary-foreground"
                        : "bg-primary text-primary-foreground"
                }`}
                aria-label={playing ? "Pause" : "Play"}
            >
                {playing ? <Pause size={14} /> : <Play size={14} />}
            </button>
            <audio
                ref={audioRef}
                src={fileSrc(src)}
                onTimeUpdate={onTime}
                onEnded={() => {
                    setPlaying(false);
                    setProgress(0);
                }}
                preload="metadata"
                className="hidden"
            />
            {/* Fake waveform using 18 bars */}
            <div className="flex h-6 items-end gap-[2px]">
                {Array.from({ length: 18 }).map((_, i) => {
                    const active = i / 18 <= progress;
                    const h = ((i * 7) % 18) + 6;
                    return (
                        <span
                            key={i}
                            className={`w-[2px] rounded-full transition-colors ${
                                active
                                    ? mine
                                        ? "bg-primary-foreground"
                                        : "bg-primary"
                                    : mine
                                    ? "bg-primary-foreground/40"
                                    : "bg-border"
                            }`}
                            style={{ height: `${h}px` }}
                        />
                    );
                })}
            </div>
            <span className={`text-[10px] font-semibold tabular-nums ${mine ? "text-primary-foreground/90" : "text-muted-foreground"}`}>
                {`${mins}:${String(secs).padStart(2, "0")}`}
            </span>
        </div>
    );
}
