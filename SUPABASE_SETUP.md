# Hướng Dẫn Cài Đặt Database CrowdSight Trên Supabase

Tài liệu này hướng dẫn thiết lập hoàn chỉnh database PostgreSQL trên Supabase cho dự án **CrowdSight** chỉ với vài thao tác nhanh gọn.

---

## 1. Khởi Tạo Schema (Bắt Buộc)

1. Mở **Supabase Dashboard**: [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Chọn dự án của bạn (hoặc tạo dự án mới).
3. Ở thanh menu bên trái, chọn **SQL Editor** (biểu tượng `>_`).
4. Bấm **+ New query**.
5. Mở file [supabase_schema.sql](file:///d:/Project-Gascolae/CrowdSight/supabase_schema.sql), sao chép toàn bộ nội dung (Ctrl + A, Ctrl + C).
6. Dán vào ô soạn thảo query của Supabase (Ctrl + V).
7. Bấm nút **Run** (hoặc nhấn `Ctrl + Enter`).
8. Thông báo `Success. No rows returned` xuất hiện ➔ **Toàn bộ 9 bảng, khóa ngoại, chỉ mục, check constraint và trigger đã được tạo thành công!**

---

## 2. Nạp Dữ Liệu Thực Tế (Data Seed)

> [!TIP]
> **Định Dạng ID Rõ Ràng, Có Thứ Tự (Không dùng UUID ngẫu nhiên)**:
> Toàn bộ ID của hệ thống đã được chuẩn hóa lại theo mẫu dễ đọc và có thứ tự rõ ràng:
> - **Video**: `media-01-crowd6`, `media-02-150`, `media-03-crowd`
> - **Session**: `session-01-crowd6`, `session-02-crowd`, `session-03-150`
> - **Artifact**: `art-01-crowd6-dataset`, `art-01-crowd6-heatmap`, ...
> - **Zone Version**: `zsv-crowd6-v1`..`v3`, `zsv-150-v1`..`v4`
> - **Observation**: `obs-crowd6-f0000`..`f0627`, `obs-150-f0000`..`f1435`
> - **Zone Result**: `zr-00001` .. `zr-04468`
>
> Mỗi file đều được chia nhỏ **<= 580 KB** tại [supabase_seeds/](file:///d:/Project-Gascolae/CrowdSight/supabase_seeds) để không bao giờ bị lỗi kích thước trên Supabase.

---

### CÁCH 1: Copy / Paste trên Supabase SQL Editor

Mở thư mục [supabase_seeds/](file:///d:/Project-Gascolae/CrowdSight/supabase_seeds) và chạy theo thứ tự:

0. **Bước 0 (Nếu bảng đã có dữ liệu UUID cũ cần xóa sạch để nạp mới)**:
   - Mở file [00_clean_database.sql](file:///d:/Project-Gascolae/CrowdSight/supabase_seeds/00_clean_database.sql).
   - Paste vào SQL Editor và bấm **Run** (lệnh này sẽ dọn sạch dữ liệu cũ để sẵn sàng nhận ID mới).

1. **Bước 1 (Bắt buộc - Core Metadata)**:
   - Mở file [01_core_metadata.sql](file:///d:/Project-Gascolae/CrowdSight/supabase_seeds/01_core_metadata.sql) (**9.1 KB**).
   - Paste vào SQL Editor và bấm **Run**.
   - *Kết quả*: Tạo 3 video, 2 zone sets, 7 phiên bản zone, 3 sessions, và 6 artifacts với ID chuẩn đẹp.

2. **Bước 2 (Bắt buộc - Zone Results)**:
   - Mở file [02_zone_results.sql](file:///d:/Project-Gascolae/CrowdSight/supabase_seeds/02_zone_results.sql) (**509 KB**).
   - Paste vào SQL Editor và bấm **Run**.
   - *Kết quả*: Nạp toàn bộ 4,468 dòng kết quả thống kê zone (`zr-00001` $\to$ `zr-04468`).

3. **Bước 3 (Chọn 1 trong 2 lựa chọn)**:
   - **Lựa chọn A - Dùng mẫu nhanh (Khuyên dùng khi muốn test ngay)**:
     - Mở file [03_observations_sample_crowd6.sql](file:///d:/Project-Gascolae/CrowdSight/supabase_seeds/03_observations_sample_crowd6.sql) (**449 KB**).
     - Paste và bấm **Run**.
     - Có ngay 10 khung hình mẫu (`obs-crowd6-f0000` $\to$ `f0009`) chứa đầy đủ ~300 bboxes/frame để preview giao diện!
   - **Lựa chọn B - Nạp toàn bộ lịch sử (59 phần)**:
     - Các file từ `obs_part_01_of_59.sql` đến `obs_part_59_of_59.sql` trong thư mục [supabase_seeds/observations/](file:///d:/Project-Gascolae/CrowdSight/supabase_seeds/observations) (mỗi file **~550 KB**).
     - Paste lần lượt các file bạn cần vào SQL Editor và bấm **Run**.

---

### CÁCH 2: Nạp Toàn Bộ Bằng 1 Lệnh Terminal (Nhanh Nhất)

Nếu bạn muốn nạp toàn bộ 100% dữ liệu (toàn bộ 2,234 frame detection) mà không cần copy/paste 59 lần:

1. Lấy chuỗi kết nối Database URI từ Supabase:
   - Vào Supabase Dashboard ➔ **Project Settings** ➔ **Database** ➔ Cuộn xuống mục **Connection string** ➔ Chọn tab **URI**.
   - Ví dụ: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`

2. Chạy lệnh:
   ```bash
   python scripts/load_supabase.py --db-url "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
   ```

Script sẽ tự động nạp toàn bộ dữ liệu vào Supabase trong ~10 giây với thanh tiến trình trực quan.

---

## 3. Kiểm Tra Kết Quả

Chạy câu lệnh SQL sau trong **SQL Editor** để kiểm tra:

```sql
SELECT 'media_assets' AS table_name, count(*) AS total_rows FROM media_assets
UNION ALL SELECT 'zone_sets', count(*) FROM zone_sets
UNION ALL SELECT 'zone_set_versions', count(*) FROM zone_set_versions
UNION ALL SELECT 'sessions', count(*) FROM sessions
UNION ALL SELECT 'zone_results', count(*) FROM zone_results
UNION ALL SELECT 'observations', count(*) FROM observations
UNION ALL SELECT 'artifacts', count(*) FROM artifacts
UNION ALL SELECT 'audit_log', count(*) FROM audit_log;
```

Kết quả mong đợi sau khi nạp đầy đủ:
- `media_assets`: **3** (`media-01-crowd6`, `media-02-150`, `media-03-crowd`)
- `zone_sets`: **2** (`zones-crowd6`, `zones-150`)
- `zone_set_versions`: **7** (`zsv-crowd6-v1..v3`, `zsv-150-v1..v4`)
- `sessions`: **3** (`session-01-crowd6`, `session-02-crowd`, `session-03-150`)
- `zone_results`: **4,468** (`zr-00001` .. `zr-04468`)
- `observations`: **2,234** (hoặc **10** nếu dùng mẫu nhanh)
- `artifacts`: **6** (`art-01-crowd6-dataset`, `art-01-crowd6-heatmap`, ...)
- `audit_log`: **1** (`audit-0001`)

---

## 4. Cấu Hình Backend Kết Nối Tới Supabase (Sau Này)

Khi bạn muốn chuyển backend FastAPI từ SQLite sang Supabase:

```env
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```
SQLAlchemy models hiện tại của CrowdSight tương thích 100% với schema trên, không cần sửa đổi bất kỳ code logic nào.
