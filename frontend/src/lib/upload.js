import { api, formatApiError } from "./api";

export async function uploadFile(file) {
    const fd = new FormData();
    fd.append("file", file);
    const { data } = await api.post("/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
    });
    return data; // { url, path, ... }
}

export function fileSrc(url) {
    if (!url) return url;
    if (url.startsWith("http") || url.startsWith("data:")) return url;
    const base = process.env.REACT_APP_BACKEND_URL || "";
    return `${base}${url}`;
}

export { formatApiError };
