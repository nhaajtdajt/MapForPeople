import { useEffect, useId, useRef, useState } from "react";

import { api, isAbort, type PlaceDetail, type Suggestion } from "../api";

const MIN_CHARS = 2;
const DEBOUNCE_MS = 300;

interface Props {
  near: { lat: number; lon: number };
  onPick: (place: PlaceDetail) => void;
}

type Status = "idle" | "loading" | "empty" | "error";

export default function SearchBar({ near, onPick }: Props) {
  const [text, setText] = useState("");
  const [items, setItems] = useState<Suggestion[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [open, setOpen] = useState(false);
  const nearRef = useRef(near);
  nearRef.current = near;
  const listId = useId();

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

  async function choose(item: Suggestion) {
    setOpen(false);
    setText(item.main);
    try {
      onPick(await api.placeDetail(item.place_id));
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Không tìm được địa điểm lúc này");
      setOpen(true);
    }
  }

  const showPanel = open && text.trim().length >= MIN_CHARS && (items.length > 0 || status !== "idle");

  return (
    <div className="relative flex-1">
      <div className="flex h-12 items-center gap-2 rounded-xl bg-white px-3 shadow-md ring-1 ring-slate-200 focus-within:ring-2 focus-within:ring-blue-600">
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-slate-500" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          role="combobox"
          aria-expanded={showPanel}
          aria-controls={listId}
          aria-label="Tìm địa điểm"
          placeholder="Tìm địa điểm"
          autoComplete="off"
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          className="h-full min-w-0 flex-1 bg-transparent text-base text-slate-900 outline-none placeholder:text-slate-500"
        />
        {text && (
          <button
            type="button"
            aria-label="Xóa nội dung tìm kiếm"
            onClick={() => {
              setText("");
              setItems([]);
            }}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100"
          >
            ×
          </button>
        )}
      </div>

      {showPanel && (
        <ul
          id={listId}
          role="listbox"
          className="absolute left-0 right-0 top-14 z-20 max-h-72 overflow-auto rounded-xl bg-white py-1 shadow-lg ring-1 ring-slate-200"
        >
          {status === "loading" && items.length === 0 && <li className="px-4 py-3 text-sm text-slate-600">Đang tìm…</li>}
          {status === "empty" && <li className="px-4 py-3 text-sm text-slate-600">Không thấy địa điểm nào khớp</li>}
          {status === "error" && (
            <li role="alert" className="px-4 py-3 text-sm text-red-700">
              {message}
            </li>
          )}
          {items.map((item) => (
            <li key={item.place_id} role="option" aria-selected={false}>
              <button
                type="button"
                onClick={() => void choose(item)}
                className="flex min-h-12 w-full flex-col justify-center px-4 py-2 text-left hover:bg-slate-50"
              >
                <span className="text-base text-slate-900">{item.main}</span>
                {item.secondary && <span className="text-sm text-slate-600">{item.secondary}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
