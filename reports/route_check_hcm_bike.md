# Đối chiếu thuật toán tìm đường với Goong: TP. Hồ Chí Minh, bike

Chạy lúc 21:56 Sunday 04/10/2026 (giờ Việt Nam), 25 cặp điểm cách nhau 3–15 km.

Goong là mốc tham chiếu, không phải sự thật. Giờ chạy cho biết đường lúc đó vắng hay đông.

| Chỉ số | Kết quả |
|---|---|
| Chiều dài ta / Goong | trung vị 0.999 (p10–p90: 0.906–1.054) |
| Thời gian ta / Goong | trung vị 0.991 (p10–p90: 0.929–1.096) |
| Mức trùng của hai đường (trong 30 m) | trung bình 0.685, trung vị 0.897 |
| Số cặp trùng dưới 50% / từ 90% | 9 / 12 |

**Gợi ý:** nhân mọi tốc độ trong `SPEEDS_KMH["bike"]` với 1.009 thì thời gian của ta khớp Goong ở trung vị (tỉ lệ thời gian trên 1 nghĩa là ta ước lâu hơn Goong, dưới 1 nghĩa là nhanh hơn).

## Năm cặp ít trùng nhất (để mở trên bản đồ xem vì sao)

| Mức trùng | Chiều dài ta / Goong | Thời gian ta / Goong | Từ | Tới |
|---|---|---|---|---|
| 0.01 | 1.03 | 1.03 | nút 31589 | nút 10782 |
| 0.02 | 1.19 | 0.99 | nút 52876 | nút 115884 |
| 0.20 | 1.01 | 0.99 | nút 26879 | nút 119278 |
| 0.35 | 0.75 | 1.00 | nút 79626 | nút 112469 |
| 0.38 | 1.02 | 0.98 | nút 51436 | nút 94596 |
