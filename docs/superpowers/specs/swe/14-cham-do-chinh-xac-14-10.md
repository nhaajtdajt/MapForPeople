# Chấm độ chính xác trên số liệu thật, tuần 07–14/10/2026

Ngày chấm: 14/10/2026. Số liệu: số đo thật trạm Phú An (51 lần đo, 07/10 01:00 tới 14/10 07:00), mưa từng giờ 44 trạm (7 ngày, cổng vndms chỉ giữ chừng đó), lịch triều biển Open-Meteo, và tin ngập trên báo (nguồn ở cuối trang). Không dùng bộ khóa 2025–2026 của repo mô hình.

## 1. Mô hình 1, phần triều: đoán đúng chỗ ngập

Tuần này có triều cường: Phú An đo 1,60–1,72 m ở các đỉnh triều từ 10 tới 13/10 (báo động 3 là 1,60 m). Báo chí đưa tin ngập trên 7 đường: Trần Xuân Soạn, Phạm Hữu Lầu, Huỳnh Tấn Phát, Bùi Văn Ba, Võ Thị Nhờ, Nguyễn Bình, Lê Văn Lương (99 đoạn trong bảng tuyến). Kiểm thêm 37 điểm ngập do triều của PC08.

| Phần đầu bảng xếp hạng triều | Số tuyến | Đoạn báo đưa tin nằm trong | Đường có ít nhất một đoạn | Điểm PC08 |
|---|---|---|---|---|
| 2% | 2.804 | 37/99 | 7/7 | 22/37 |
| 5% (nhóm A) | 7.011 | 63/99 | 7/7 | 30/37 |
| 10% | 14.023 | 87/99 | 7/7 | 37/37 |
| 20% (nhóm A + B) | 28.047 | 94/99 | 7/7 | 37/37 |

Chọn bừa thì 5% đầu bảng chỉ chứa khoảng 5% số đoạn. Phần lớn các đoạn báo đưa tin không có trong lịch sử ngập mà mô hình học, nên đây là đoán đúng chỗ mô hình chưa thấy.

## 2. Dự báo triều Phú An: đoán đúng giờ ngập

Cách chấm: tại mỗi lần đo, chỉ dùng số đo có trước đó H giờ để khớp lịch triều biển về Phú An, rồi đoán mực nước.

| Đoán trước | Sai trung bình | Giờ thật từ 1,40 m | Đoán trúng | Báo nhầm |
|---|---|---|---|---|
| 3 giờ | 0,15 m | 13 | 12 | 0 |
| 6 giờ | 0,15 m | 13 | 12 | 0 |
| 24 giờ | 0,16 m | 13 | 12 | 0 |

Ở ngưỡng 1,50 m và 1,60 m: đúng 35–37 trên 37–38 lần. Đã thử năm cách khớp khác (khớp 3 ngày gần nhất, đè nặng nước cao, bậc hai...): không cách nào hơn rõ, nên giữ cách đang dùng.

## 3. Thay đổi đã làm để tăng độ chính xác

**Tô màu theo bậc triều** (`src/floodrisk/live/local.py`, `TIDE_STEPS`). Trước: Phú An từ 1,50 m thì tô 20% số tuyến (nhóm A đỏ, nhóm B vàng); mức này tuần này đạt hai lần mỗi ngày, trong khi mọi tin ngập đều ở mức từ 1,60 m. Nay triều càng cao càng tô rộng:

| Phú An | Tô đỏ | Có màu |
|---|---|---|
| dưới 1,40 m | 0 | 0 |
| 1,40–1,49 m (báo động 1) | 0 | 2% đầu bảng |
| 1,50–1,59 m (báo động 2) | 2% | 5% |
| 1,60–1,69 m (báo động 3) | 5% | 10% |
| từ 1,70 m | 5% | 20% |

Chấm trên từng giờ của tuần (mực nước nội suy theo lịch triều giữa các lần đo):

| | Quy tắc cũ | Theo bậc |
|---|---|---|
| Tổng km-giờ bị tô cả tuần | 334.508 | 188.348 (giảm 44%) |
| km-giờ bị tô ngoài giờ có tin ngập | 98.262 | 38.687 (giảm 61%) |
| Giờ có tin ngập, triều từ 1,60 m: đoạn báo đưa tin được tô đỏ / có màu | 64% / 95% | 64% / 91% |

Các bậc là số tròn đặt trước khi chấm, nhưng mới thử trên một đợt triều; cần chấm lại sau đợt triều cường 27–29/10.

**Mực nước Phú An thay cho trạng thái triều của Mô hình 2** khi có số: trước lấy mức lớn hơn, nên khi triều thiên văn Vũng Tàu báo động thì cả thành phố đỏ dù Phú An còn thấp.

**Dự báo triều 12 giờ tới** trên dòng trạng thái: "đỉnh triều 1,60 m lúc 05:00".

**Đề xuất đường**: trước xếp theo mét đã xác nhận ngập rồi mét từng ngập trong lịch sử, nên lúc triều báo động tối 14/10 app đề xuất đường có 3,6 km đỏ thay cho đường 2,2 km đỏ. Nay xếp theo mét đã xác nhận, rồi mét đang ở mức cao, rồi lịch sử, rồi thời gian.

**Nhãn "Đang dùng bản giả"** không còn hiện trên dữ liệu thật (báo cáo người dùng là thật).

## 4. Chưa chấm được

- **Mưa**: 7 ngày qua chỉ có 08/10 mưa to (7 trạm vượt 30 mm/giờ). Không tìm thấy tin ngập do mưa từ 10 tới 13/10. Cần thêm ngày mưa; bộ ghi (`tools/ghi_du_lieu.py`) lưu đủ để chấm khi có.
- **Camera Gemini**: chưa gặp cảnh ngập thật.

## Nguồn tin ngập

- [Dân trí, 10/10: Triều cường dâng cao, đường phố TPHCM ngập gần nửa mét](https://dantri.com.vn/dt360/trieu-cuong-dang-cao-duong-pho-tphcm-ngap-gan-nua-met-20261010190600412.htm)
- [VnExpress: Nhiều đường TP HCM ngập sâu do triều cường cao nhất từ đầu năm](https://vnexpress.net/nhieu-duong-tp-hcm-ngap-sau-do-trieu-cuong-cao-nhat-tu-dau-nam-5130779.html)
- [DKN, 11/10: Triều cường gây ngập nhiều tuyến đường TP.HCM sáng 11/10](https://mb.dkn.tv/thoi-su/trieu-cuong-gay-ngap-nhieu-tuyen-duong-tphcm-sang-1110.html)
- [Tuổi Trẻ, 11/10: Nhiều tuyến đường ở TP.HCM ngập vì triều cường đạt đỉnh](https://tuoitre.vn/nhieu-tuyen-duong-o-tphcm-ngap-vi-trieu-cuong-dat-dinh-100261011145716767.htm)
- [Thanh Niên, 11/10: Chiều nay triều cường đạt đỉnh, đường ngập sâu](https://thanhnien.vn/chieu-nay-1110-trieu-cuong-dat-dinh-duong-o-tphcm-ngap-sau-nuoc-tran-vao-nha-dan-18526101116245377.htm)
- [Báo Mới (SGGP): Nhiều nơi trũng thấp tại TPHCM tiếp tục ngập do triều cường](https://baomoi.com/nhieu-noi-trung-thap-tai-tphcm-tiep-tuc-ngap-do-trieu-cuong-c56261750.epi)
- [Thanh Niên: Đón đỉnh triều cường cao nhất tháng 10](https://thanhnien.vn/don-dinh-trieu-cuong-cao-nhat-thang-10-tphcm-va-mien-tay-nguy-co-ngap-sau-dai-ngay-18526101016453984.htm)
