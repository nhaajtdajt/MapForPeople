import { useEffect, useRef, useState } from "react";

import { api, isAbort, type Suggestion } from "../api";

export const MIN_CHARS = 2;
const DEBOUNCE_MS = 300;
export type SearchStatus = "idle" | "loading" | "empty" | "error";

/** Gợi ý địa điểm cho một ô tìm kiếm: chờ người dùng ngừng gõ 300 ms rồi mới hỏi, hủy lượt hỏi cũ khi gõ tiếp. */
export function usePlaceSearch(text: string, near: { lat: number; lon: number }) {
  const [items, setItems] = useState<Suggestion[]>([]);
  const [status, setStatus] = useState<SearchStatus>("idle");
  const [message, setMessage] = useState("");
  const nearRef = useRef(near);
  nearRef.current = near;

  useEffect(() => {
    const query = text.trim();
    if (query.length < MIN_CHARS) {
      setItems([]);
      setStatus("idle");
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setStatus("loading");
      try {
        const found = await api.autocomplete(query, nearRef.current, controller.signal);
        setItems(found);
        setStatus(found.length === 0 ? "empty" : "idle");
      } catch (error) {
        if (isAbort(error)) return;
        setItems([]);
        setStatus("error");
        setMessage(error instanceof Error ? error.message : "Không tìm được địa điểm lúc này");
      }
    }, DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [text]);

  return { items, status, message, setStatus, setMessage, clear: () => setItems([]) };
}
