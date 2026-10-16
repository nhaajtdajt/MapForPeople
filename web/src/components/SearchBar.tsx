import { useId, useState } from "react";

import { api, type PlaceDetail, type Suggestion } from "../api";
import { MIN_CHARS, usePlaceSearch } from "../lib/usePlaceSearch";
import Icon from "./Icon";

interface Props {
  near: { lat: number; lon: number };
  onPick: (place: PlaceDetail) => void;
}

export default function SearchBar({ near, onPick }: Props) {
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const { items, status, message, setStatus, setMessage, clear } = usePlaceSearch(text, near);
  const listId = useId();

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
      <div className="flex h-12 items-center gap-2.5 rounded-2xl bg-white pl-3.5 pr-1 shadow-float transition-shadow focus-within:ring-2 focus-within:ring-brand">
        <Icon name="search" className="h-5 w-5 shrink-0 text-ink-faint" />
        <input
          type="search"
          role="combobox"
          aria-expanded={showPanel}
          aria-controls={listId}
          aria-label="Tìm địa điểm"
          placeholder="Tìm đường, địa điểm"
          autoComplete="off"
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          className="h-full min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-ink-faint focus-visible:outline-none"
        />
        {text && (
          <button
            type="button"
            aria-label="Xóa nội dung tìm kiếm"
            onClick={() => {
              setText("");
              clear();
            }}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-ink-faint hover:bg-mist hover:text-ink"
          >
            <Icon name="close" className="h-4.5 w-4.5" />
          </button>
        )}
      </div>

      {showPanel && (
        <ul
          id={listId}
          role="listbox"
          className="pop-in absolute left-0 right-0 top-14 z-20 max-h-72 overflow-auto rounded-2xl bg-white py-1.5 shadow-float ring-1 ring-line"
        >
          {status === "loading" && items.length === 0 && <li className="px-4 py-3 text-sm text-ink-faint">Đang tìm…</li>}
          {status === "empty" && <li className="px-4 py-3 text-sm text-ink-faint">Không thấy địa điểm nào khớp</li>}
          {status === "error" && (
            <li role="alert" className="px-4 py-3 text-sm text-danger-ink">
              {message}
            </li>
          )}
          {items.map((item) => (
            <li key={item.place_id} role="option" aria-selected={false}>
              <button
                type="button"
                onClick={() => void choose(item)}
                className="flex min-h-12 w-full flex-col justify-center px-4 py-2 text-left hover:bg-mist active:bg-line"
              >
                <span className="text-[15px] font-medium text-ink">{item.main}</span>
                {item.secondary && <span className="text-sm text-ink-faint">{item.secondary}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
