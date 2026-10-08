# Prompt cho Codex: giao diện tìm đường

Dán nguyên phần dưới đây vào Codex. Chạy Codex trong thư mục `D:\HK1 4 year\Hackathon\MapForPeople-codex` (worktree riêng, xem cuối file).

---

Bạn làm việc trong repo `MapForPeople`, nhánh `codex/route-ui`. Đây là ứng dụng bản đồ cảnh báo ngập cho người đi xe máy và ô tô ở TP.HCM: máy chủ FastAPI (`src/floodrisk/api/`), giao diện React + Vite + MapLibre + Tailwind (`web/`). Mọi chữ trên giao diện và mọi chú thích trong mã viết bằng tiếng Việt, giống mã đang có.

## Việc cần làm

Làm giao diện tìm đường. Máy chủ đã có sẵn `GET /api/route` và đã có kiểm thử; **không sửa máy chủ**.

1. Trên thẻ địa điểm (`web/src/components/PlaceCard.tsx`) hai nút "Chỉ đường tới đây" và "Đi từ đây" đang bị tắt vì chưa có hàm xử lý. Nối chúng lại:
   - "Chỉ đường tới đây": điểm đang ghim là điểm đến. Điểm đi là vị trí của người dùng nếu đã có (`setUserLocation` trong `App.tsx`, hiện bị bỏ đi), nếu chưa có thì mở bảng chỉ đường với ô điểm đi còn trống.
   - "Đi từ đây": điểm đang ghim là điểm đi, ô điểm đến còn trống.
2. Bảng chỉ đường (component mới `web/src/components/DirectionsPanel.tsx`):
   - hai ô điểm đi và điểm đến; ô trống thì người dùng điền bằng cách tìm địa điểm (dùng lại `SearchBar` hoặc lô-gic của nó) hoặc chạm vào bản đồ;
   - nút đổi chiều, nút chọn xe máy hoặc ô tô (`vehicle=bike|car`), nút đóng;
   - khi đủ hai điểm thì gọi `/api/route` và hiện danh sách lộ trình: thời gian, quãng đường, giờ tới nơi, nhãn "Đề xuất" cho lộ trình `recommended`, nhãn "Vòng xa" khi `long_detour`;
   - chọn một lộ trình thì hiện các bước đi (`steps`) của lộ trình đó;
   - hiện các dòng trong `notes` của phản hồi;
   - lỗi 404 và 422 của máy chủ có sẵn lời tiếng Việt trong `detail`: hiện đúng lời đó.
3. Trên bản đồ: vẽ mọi lộ trình trả về, lộ trình đang chọn nét đậm màu xanh dương, lộ trình khác nét nhạt màu xám; chạm vào một lộ trình nhạt thì chọn nó; ghim hai đầu; khi có kết quả thì thu phóng bản đồ vừa khít lộ trình (chừa chỗ cho bảng chỉ đường).
4. Yêu cầu mới thay yêu cầu cũ: nếu người dùng đổi điểm khi yêu cầu trước chưa về thì hủy yêu cầu trước (`AbortController`, như `handleTap` trong `App.tsx` đang làm).
5. Dùng được trên điện thoại rộng 375 px: bảng chỉ đường là tấm trượt từ dưới lên, cao tối đa nửa màn hình, cuộn được; nút bấm cao tối thiểu 44 px.

## Hợp đồng của `/api/route`

`GET /api/route?city=hcm&origin=<vĩ độ>,<kinh độ>&destination=<vĩ độ>,<kinh độ>&vehicle=bike`

Phản hồi: `{ routes: [{ id, kind, recommended, long_detour, distance_m, duration_s, arrive_at, steps: [...], geometry: { type: "LineString", coordinates: [[kinh độ, vĩ độ], ...] } }], snapped, traffic, advice, notes: [string] }`. Đọc `src/floodrisk/api/routes_route.py`, `src/floodrisk/api/graphroute.py` (hàm `steps`) và `tests/api/test_route.py` để biết chính xác các trường. Đọc thêm `docs/superpowers/specs/swe/05-tim-duong.md` cho phần giao diện; chỗ nào spec đó nói về "đoạn 200 m", "units" hay mức ngập trên lộ trình thì **bỏ qua**, phần đó người khác đang làm.

## Giới hạn, để không đụng việc của người khác

Một người khác đang sửa song song các file sau trên nhánh `web`. Hãy sửa chúng **ít nhất có thể** để gộp nhánh dễ:

- `web/src/MapView.tsx`: chỉ thêm prop cho lộ trình và gọi hàm từ file mới `web/src/lib/routeLayer.ts` (nơi bạn đặt toàn bộ mã thêm nguồn, thêm lớp, cập nhật và bắt sự kiện chạm của lộ trình). Không đổi các lớp `risk-*` và `flood-points`. Lớp lộ trình vẽ **trên** các lớp `risk-*`.
- `web/src/App.tsx`: chỉ thêm trạng thái của bảng chỉ đường và chỗ hiện component. Lô-gic đặt trong hook mới `web/src/lib/useDirections.ts`.
- `web/src/api.ts`: chỉ thêm kiểu và hàm `route`.

Không sửa: mọi thứ trong `src/`, `tests/`, `data/`, `tools/`, `docs/`, `.env*`, `web/src/lib/risk.ts`, `web/src/lib/floodnote.ts`, `web/src/components/LayersPanel.tsx`. Không thêm thư viện mới.

## Kiểm tra trước khi báo xong

Trong thư mục `web`:

```
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vitest/vitest.mjs run
node node_modules/oxlint/bin/oxlint src
```

Cả ba phải sạch. Viết kiểm thử vitest cho các hàm thuần bạn tạo ra (định dạng thời gian và quãng đường, chọn lộ trình, dựng tham số yêu cầu). Chạy thử thật. Máy chủ thường đã chạy sẵn ở cổng 8000 (kiểm bằng `http://127.0.0.1:8000/api/health`); nếu chưa thì chạy nó từ thư mục repo chính `..\MapForPeople`:

```
.venv\Scripts\python.exe -m floodrisk.api.dev --real
```

Giao diện của bạn chạy ở cổng riêng, từ thư mục này:

```
node web/node_modules/vite/bin/vite.js web --port 5174 --strictPort
```

rồi tìm đường từ chợ Bến Thành (10.7725, 106.6980) tới sân bay Tân Sơn Nhất (10.8156, 106.6640) bằng xe máy và ô tô.

## Khi xong

Commit trên nhánh `codex/route-ui` (không push, không gộp vào `web`). Báo lại: những file đã sửa, những gì đã chạy để kiểm, và những chỗ chưa làm được.

---

## Cách tạo thư mục riêng cho Codex

Chạy một lần ở gốc repo, **sau khi phần bước 1 đã được commit trên nhánh `web`**:

```
git worktree add -b codex/route-ui "..\MapForPeople-codex" web
```

Rồi chép hai thứ không nằm trong git sang thư mục mới: file `.env`, và thư mục `web\node_modules` (hoặc chạy `npm install` trong `..\MapForPeople-codex\web`). Môi trường Python dùng chung: trong thư mục mới, gọi `..\MapForPeople\.venv\Scripts\python.exe`.
