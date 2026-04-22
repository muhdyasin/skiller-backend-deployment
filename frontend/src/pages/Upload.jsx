import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, X } from "lucide-react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";

function readAsDataURL(file) {
    return new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(r.result);
        r.onerror = reject;
        r.readAsDataURL(file);
    });
}

export default function UploadPage() {
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [mediaType, setMediaType] = useState("image");
    const [caption, setCaption] = useState("");
    const [tags, setTags] = useState("");
    const [loading, setLoading] = useState(false);
    const inputRef = useRef(null);
    const navigate = useNavigate();

    const handleFile = async (f) => {
        if (!f) return;
        if (f.size > 8 * 1024 * 1024) {
            toast.error("File too large. Max 8MB for now.");
            return;
        }
        const isVideo = f.type.startsWith("video/");
        setMediaType(isVideo ? "video" : "image");
        const dataUrl = await readAsDataURL(f);
        setFile(f);
        setPreview(dataUrl);
    };

    const submit = async (e) => {
        e.preventDefault();
        if (!preview) {
            toast.error("Pick an image or video to share");
            return;
        }
        setLoading(true);
        try {
            const tagList = tags
                .split(/[\s,]+/)
                .map((t) => t.replace(/^#/, "").trim())
                .filter(Boolean);
            await api.post("/posts", {
                media: preview,
                media_type: mediaType,
                caption,
                tags: tagList,
            });
            toast.success("Posted!");
            navigate("/feed");
        } catch (err) {
            toast.error(err.response?.data?.detail || "Could not upload");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="mx-auto max-w-2xl px-4 py-6" data-testid="upload-page">
            <h1 className="font-display text-2xl font-bold tracking-tight md:text-3xl">
                Share something
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
                Post an image or video. Add a caption and tags to get discovered.
            </p>

            <form onSubmit={submit} className="mt-8 space-y-6">
                {preview ? (
                    <div className="relative overflow-hidden rounded-2xl border border-border">
                        {mediaType === "video" ? (
                            <video src={preview} controls className="w-full bg-black" />
                        ) : (
                            <img src={preview} alt="" className="max-h-[60vh] w-full object-cover" />
                        )}
                        <button
                            type="button"
                            onClick={() => {
                                setFile(null);
                                setPreview(null);
                            }}
                            className="absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full bg-background/80 backdrop-blur hover:bg-background"
                            data-testid="upload-clear-btn"
                        >
                            <X size={18} />
                        </button>
                    </div>
                ) : (
                    <button
                        type="button"
                        onClick={() => inputRef.current?.click()}
                        className="grid w-full place-items-center rounded-2xl border-2 border-dashed border-border p-12 text-center transition-colors hover:border-primary hover:bg-primary/5"
                        data-testid="upload-dropzone"
                    >
                        <UploadCloud size={36} className="text-muted-foreground" />
                        <div className="mt-3 font-semibold">Click to upload</div>
                        <div className="text-sm text-muted-foreground">
                            PNG, JPG, MP4 · up to 8 MB
                        </div>
                    </button>
                )}
                <input
                    ref={inputRef}
                    type="file"
                    accept="image/*,video/*"
                    onChange={(e) => handleFile(e.target.files?.[0])}
                    className="hidden"
                    data-testid="upload-file-input"
                />

                <div className="space-y-1.5">
                    <Label htmlFor="caption">Caption</Label>
                    <Textarea
                        id="caption"
                        value={caption}
                        onChange={(e) => setCaption(e.target.value)}
                        rows={4}
                        placeholder="What skill is this about?"
                        data-testid="upload-caption-input"
                        className="rounded-xl"
                    />
                </div>

                <div className="space-y-1.5">
                    <Label htmlFor="tags">Tags</Label>
                    <Input
                        id="tags"
                        value={tags}
                        onChange={(e) => setTags(e.target.value)}
                        placeholder="design, ui, tutorial"
                        data-testid="upload-tags-input"
                        className="rounded-xl"
                    />
                    <p className="text-xs text-muted-foreground">
                        Comma or space separated. Don't include #.
                    </p>
                </div>

                <div className="flex items-center justify-end gap-3">
                    <Button
                        type="button"
                        variant="ghost"
                        onClick={() => navigate(-1)}
                        className="rounded-full"
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        disabled={loading || !preview}
                        className="rounded-full px-6"
                        data-testid="upload-submit-btn"
                    >
                        {loading ? "Publishing…" : "Publish"}
                    </Button>
                </div>
            </form>
        </div>
    );
}
