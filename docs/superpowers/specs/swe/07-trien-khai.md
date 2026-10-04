# Spec 07: Triển khai và vận hành

**Mã theo dõi:** S7.1, S7.2 (lõi, ngày 3); S7.3 (lõi, ngày 4); S7.4 (lõi, ngày 9).

## Mục tiêu

Hết ngày 3, sản phẩm chạy trên một máy chủ công khai với dữ liệu thật của TP.HCM, để hai người kia nhìn thấy kết quả của mình trên bản đồ thật và lỗi nối ghép lộ ra sớm. Hết ngày 4 có HTTPS, vì nút định vị là một phần của bản đồ cơ bản và trình duyệt chỉ cho định vị trên trang HTTPS. Hôm trình diễn có một bản dự phòng chạy trên máy cá nhân.

Các quyết định về nơi chạy và chi phí nằm ở QĐKT mục 10.

## 1. Đóng gói và máy chủ (S7.1)

### 1.1 Một ảnh Docker

- `Dockerfile` hai bước: bước đầu dựng giao diện bằng Node; bước sau là ảnh Python 3.12 chứa gói `floodrisk` và thư mục `web/dist` vừa dựng.
- Máy chủ FastAPI phục vụ giao diện ở `/` và API ở `/api`. Đường dẫn `/api` luôn được ưu tiên hơn file tĩnh.
- `docker-compose.yml` có một dịch vụ tên `app`, gắn cả thư mục `data/` của máy vào `/data`, đặt `FLOODRISK_DATA=/data`, và truyền các biến `GOONG_API_KEY`, `TOMTOM_API_KEY`, `REFRESH_MINUTES`, `FLOODRISK_TEST_TOOLS`, `FLOODRISK_CONTACT` từ file `.env` trên máy.
- Khóa bản đồ `VITE_GOONG_MAP_KEY` đi vào lúc dựng giao diện, vì nó nằm trong mã chạy ở trình duyệt.
- `reports.sqlite` nằm trong `/data`, nên còn nguyên khi dựng lại container.

### 1.2 Máy EC2

Một máy `t3.small`, Ubuntu, vùng Singapore, ổ 30 GB; mở cổng 22 cho địa chỉ IP của nhóm và cổng 8000 cho mọi nơi (đổi sang 80 và 443 ở ngày 4). Đặt cảnh báo ngân sách AWS ở 50 đô ngay lúc tạo máy.

Tạo máy ở ngày 1, dù chưa có gì để chạy, để lỗi về tài khoản hay hạn mức lộ ra trước ngày 3.

### 1.3 Đưa dữ liệu lên máy

Thư mục `data/` không nằm trong git. Có hai loại file, đi hai đường khác nhau:

| Loại | Ví dụ | Đường đi |
|---|---|---|
| File của người dữ liệu: lớn, ít đổi | `units`, `observations`, `obs_units`, ba file mạng đường, `rain_cells`, `rain_daily` | Người dữ liệu để vào thư mục Google Drive chung, bố cục giống `data/processed/`. Kỹ sư phần mềm tải về và chép lên máy bằng `scp` |
| File của người AI: nhỏ, đổi thường xuyên | `scores`, `trigger.json`, `model_choice.json`, các kịch bản trong `replay/` | Tạo ngay trên máy EC2, bằng cách chạy lệnh của người AI bên trong container: `docker compose exec app python -m floodrisk.model.…` |
| File tự sinh | `risk.parquet`, `raw/inputs/` | Tác vụ nền ghi mỗi giờ |

Cách thứ hai tránh được việc chép tay mỗi lần người AI sửa mô hình: mã đi qua git, và kết quả được tính lại tại chỗ.

Mỗi lần chép file mới lên, chạy `docker compose exec app python -m floodrisk.api.doctor hcm` trước khi khởi động lại.

File `deploy/README.md` ghi lại đúng chuỗi lệnh đã dùng: tạo máy, cài Docker, lấy mã, chép dữ liệu, dựng và chạy. Người khác trong nhóm phải làm lại được chỉ bằng file đó.

### 1.4 Mốc ngày 3

Bốn điều kiện, lấy từ KH04 mục E và sửa theo thứ tự làm mới (báo ngập lùi sang ngày 4, tìm đường kéo lên ngày 2):

1. `units`, `scores`, `risk` và ba file mạng đường thật của TP.HCM nằm trong `data/processed/hcm/` trên máy EC2.
2. Container chạy bằng `docker compose up -d --build`, truy cập được qua `http://<địa chỉ IP>:8000`.
3. Bản đồ hiện lớp nguy cơ thật; ô chọn chế độ có ít nhất một ngày phát lại; tìm đường giữa hai điểm ở TP.HCM trả lộ trình trên đường thật.
4. Tác vụ nền chạy mỗi giờ, và chú thích không còn dòng "chưa được cập nhật".

Nếu tới trưa ngày 3 mà file thật chưa đến, vẫn triển khai với `data/sample` để kiểm đường ống Docker và máy chủ, rồi thay dữ liệu khi có. Mốc chỉ được ghi là đạt khi cả bốn điều kiện đúng với dữ liệu thật.

Kiểm bộ nhớ ngay sau lần chạy đầu bằng `docker stats`. Nếu máy `t3.small` (2 GB) dùng quá 1,5 GB khi nạp TP.HCM thì đổi lên `t3.medium` và báo nhóm.

## 2. Tác vụ nền mỗi giờ (S7.2)

- Khi `REFRESH_MINUTES` lớn hơn 0, máy chủ gọi `ports.run_hourly` một lần ngay lúc khởi động, rồi lặp lại sau mỗi `REFRESH_MINUTES` phút. Tác vụ chạy trong một luồng riêng để không chặn các yêu cầu.
- Sau mỗi lần chạy xong, máy chủ nạp lại `risk.parquet` của các thành phố vừa được tính.
- Tác vụ lỗi thì máy chủ vẫn chạy và giữ bảng nguy cơ cũ. `GET /api/health` ghi `last_refresh` (lần chạy xong gần nhất) và `last_error` (lời lỗi gần nhất, rỗng khi lần gần nhất thành công).
- Bảng nguy cơ cũ hơn 3 giờ làm `stale` đúng, và giao diện ghi "Chưa được cập nhật từ HH:MM" (spec 02).
- `REFRESH_MINUTES=0` tắt hẳn tác vụ. Đây là giá trị lúc phát triển và lúc chạy bản dự phòng.
- **Tác vụ nền thứ hai, cho giao thông:** khi có `TOMTOM_API_KEY`, máy chủ lấy số liệu giao thông mỗi 10 phút từ 6 tới 23 giờ (spec 09). Tác vụ này độc lập với tác vụ mỗi giờ; nó lỗi thì giao thông lùi về bảng điển hình. Không có khóa thì tác vụ không chạy.

## 3. Tên miền và HTTPS (S7.3)

Trình duyệt chỉ cho định vị trên trang HTTPS, nên nút "Vị trí của tôi" không hoạt động trên máy chủ cho tới khi làm xong mục này. Vì vậy nó được làm ở ngày 4, ngay sau mốc ngày 3.

- Kỹ sư phần mềm lo một tên miền. Để kịp ngày 4, dùng một tên miền con miễn phí (ví dụ của DuckDNS) trỏ về địa chỉ IP của máy; đổi sang tên miền đẹp hơn sau nếu muốn.
- Gắn một địa chỉ IP cố định (Elastic IP) cho máy trước khi trỏ tên miền.
- Caddy chạy trước container, tự xin và gia hạn chứng chỉ, chuyển tiếp sang cổng 8000. Thêm Caddy vào `docker-compose.yml` như một dịch vụ thứ hai.
- Sau khi có tên miền: giới hạn khóa bản đồ của Goong theo tên miền đó trong trang quản lý Goong, và giới hạn khóa REST theo địa chỉ IP của máy.
- Máy chủ chỉ chấp nhận yêu cầu từ trang cùng nguồn; không bật CORS cho mọi nơi.

## 4. Bản dự phòng cho buổi trình diễn (S7.4)

Mạng ở hội trường có thể hỏng, và máy EC2 có thể hỏng đúng lúc.

- Một máy cá nhân chạy đúng ảnh Docker đó, với một bản sao thư mục `data/` lấy từ máy EC2 trong ngày 9, `REFRESH_MINUTES=0`, ở chế độ phát lại.
- Bản dự phòng vẫn cần mạng để tải nền bản đồ Goong. Nếu mất mạng hoàn toàn thì dùng đoạn phim quay sẵn.
- Quay một đoạn phim màn hình chạy trọn kịch bản trình diễn trên máy EC2, trong ngày 9.
- Kịch bản trình diễn được viết thành một danh sách bước trong `deploy/DEMO.md`, mỗi bước kèm liên kết mở đúng trạng thái nếu S4.3 đã làm.
- Bàn thử ở bản công khai để tắt. Nếu muốn dùng bàn thử trong buổi trình diễn thì bật nó trên bản dự phòng, không bật trên bản công khai.

## 5. Chỗ đang dùng bản giả

| Cần | Bản giả | Bản thật đến khi nào |
|---|---|---|
| `run_hourly` | Không làm gì, trả danh sách rỗng | Hết ngày 2 |
| Dữ liệu trên máy EC2 | `data/sample`, chỉ để kiểm đường ống | Trưa và hết ngày 2 |

## 6. Nghiệm thu

**S7.1:**

- [ ] `docker compose up --build` trên máy cá nhân với `data/sample`: mở `http://localhost:8000` thấy giao diện, `/api/health` trả lời.
- [ ] Dựng lại container không làm mất `reports.sqlite`.
- [ ] Máy EC2 đã tạo, có cảnh báo ngân sách 50 đô.
- [ ] `deploy/README.md` có đủ chuỗi lệnh, và một người khác trong nhóm đã đọc.
- [ ] Bốn điều kiện của mốc ngày 3 đạt với dữ liệu thật. Ghi ngày đạt: ……
- [ ] Bộ nhớ dùng trên máy EC2 sau khi nạp TP.HCM: …… MB.

**S7.2:**

- [ ] Tác vụ chạy một lần lúc khởi động khi `REFRESH_MINUTES` bằng 60, và không chạy khi bằng 0.
- [ ] Tác vụ ném lỗi thì máy chủ vẫn trả lời, và `last_error` có lời lỗi đó.
- [ ] Sau một lần chạy thành công, `GET /api/risk` trả `computed_at` mới mà không phải khởi động lại.

**S7.3:**

- [ ] Trang mở được bằng HTTPS trên tên miền của nhóm, chứng chỉ hợp lệ.
- [ ] Nút "Vị trí của tôi" hoạt động trên điện thoại.
- [ ] Hai khóa Goong đã được giới hạn theo tên miền và địa chỉ IP.

**S7.4:**

- [ ] Bản dự phòng chạy trọn kịch bản trình diễn trên máy cá nhân.
- [ ] Có đoạn phim quay màn hình.
- [ ] `deploy/DEMO.md` có danh sách bước.
- [ ] `/api/health` trên máy EC2 ghi `data` là `real` và không còn phần nào là `fake`.

## 7. Không làm

- Không dùng cơ sở dữ liệu riêng (PostgreSQL), không cân bằng tải, không nhiều máy. Đã cân nhắc và để sau hackathon (QĐKT mục 1).
- Không dựng quy trình tự động triển khai. Cập nhật bằng `git pull` và `docker compose up -d --build` trên máy.
- Không bắt buộc sao lưu lên S3.
