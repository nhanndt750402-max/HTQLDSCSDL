# HTQLDSCSDL
# HỆ THỐNG QUẢN LÝ MƯỢN TRẢ SÁCH THƯ VIỆN (PYTHON + SQLITE)

## 1. Giới thiệu & Phân công thành viên
Dự án xây dựng hệ thống quản lý thư viện sử dụng Python và cơ sở dữ liệu quan hệ SQLite (`thuvien.db`), hỗ trợ song song hai giao diện: **CLI (dòng lệnh)** và **GUI (cửa sổ Tkinter)**.

### Các tính năng & Quy tắc nghiệp vụ chính
* **Khởi tạo dữ liệu động & An toàn:** Tự động thiết lập lược đồ CSDL chuẩn hóa (kèm khóa chính, khóa ngoại, chỉ mục Index) và sinh bộ dữ liệu mẫu dựa trên Mã số sinh viên (MSSV), tích hợp cơ chế chống ghi đè dữ liệu hiện có.
* **Quản lý danh mục (CRUD):** Thêm, xem, cập nhật, xóa thông tin Sách và Độc giả; tra cứu lịch sử mượn trả chi tiết của từng độc giả.
* **Kiểm soát quy trình Mượn / Trả (Transaction):**
  * Tự động tính hạn trả tiêu chuẩn (**14 ngày** kể từ ngày mượn) và cập nhật số lượng tồn kho theo thời gian thực.
  * Áp dụng chặt chẽ các ràng buộc nghiệp vụ: giới hạn tối đa **3 cuốn sách** đang mượn/độc giả, chặn mượn trùng đầu sách đang giữ, chặn mượn khi sách đã hết tồn kho và chặn xác nhận trả trùng phiếu đã hoàn tất.
* **Quản lý phạt trễ hạn & Thống kê:**
  * Tự động tính phí phạt quá hạn (**5.000 VNĐ/ngày**), khóa quyền mượn mới đối với độc giả đang nợ phạt và mở khóa ngay sau khi thanh toán.
  * Thống kê **Top 5 đầu sách** được mượn nhiều nhất tại thư viện.
* **Giao diện đa chế độ:** Hỗ trợ giao diện dòng lệnh (CLI) hiển thị bảng kẻ khung chuẩn SQL và giao diện cửa sổ trực quan (Tkinter GUI) tích hợp nút chuyển đổi/tái tạo dữ liệu theo MSSV.

| Thành viên | Phụ trách | Tệp tin chính |
| :--- | :--- | :--- |
| **TV1** | Thiết kế CSDL, ràng buộc khóa ngoại & sinh dữ liệu mẫu theo MSSV | `database.py`, `seed_data.py` |
| **TV2** | Các thao tác CRUD Sách, Độc giả, truy vấn lịch sử & đánh Index | `sql.py` |
| **TV3** | Nghiệp vụ cốt lõi Mượn / Trả sách, kiểm soát giao dịch (Transaction) | `business_logic.py` |
| **TV4** | Tính phạt trễ hạn tự động, kiểm tra nợ phạt, thanh toán & Top 5 sách | `advanced_logic1.py` |
| **TV5** | Giao diện người dùng đồ họa (Tkinter) & bộ chuyển đổi dữ liệu | `main_gui.py`, `ui_adapter.py` |
| **TV6** | Giao diện CLI tổng hợp, kiểm thử tự động (QA/QC) & tài liệu dự án | `main.py`, `tests/test_thuvien.py`, `README.md` |

---

## 2. Yêu cầu hệ thống & Khởi chạy

### Yêu cầu
* Python 3.10 trở lên (sử dụng thư viện chuẩn `sqlite3`, `tkinter`, `unittest` — không cần cài thư viện ngoài).

### Cách chạy chương trình
Mở Terminal tại thư mục gốc của dự án và chạy một trong hai chế độ:

1. **Chạy giao diện dòng lệnh (CLI - Bảng chuẩn SQL):**
   ```bash
   python main.py
   ```
2. **Chạy giao diện cửa sổ đồ họa (Tkinter GUI):**
   ```bash
   python main_gui.py
   ```
*(Lần đầu khởi chạy nếu chưa có `thuvien.db`, hệ thống sẽ yêu cầu nhập MSSV để sinh dữ liệu mẫu tự động).*

---

## 3. Kiểm thử tự động (QA/QC)

Chạy toàn bộ bộ kiểm thử bằng lệnh:
```bash
python -m unittest discover -s tests -v
```

### Nội dung các ca kiểm thử (`tests/test_thuvien.py`)
1. `test_01_khoi_tao_du_lieu_va_chong_ghi_de`: Kiểm tra sinh dữ liệu theo MSSV và cơ chế chặn ghi đè CSDL đã tồn tại.
2. `test_02_crud_doc_gia_va_sach`: Kiểm tra thêm, sửa, xóa Độc giả và Sách.
3. `test_03_muon_sach_thanh_cong`: Kiểm tra tạo phiếu mượn hợp lệ, tính hạn trả 14 ngày và trừ tồn kho.
4. `test_04_chan_muon_vi_pham_quy_tac`: Kiểm tra chặn mượn trùng đầu sách (R5), sách hết tồn kho (R6) và vượt giới hạn 3 cuốn (R4).
5. `test_05_tra_sach_va_tinh_phat`: Kiểm tra trả sách trễ hạn (5.000 VNĐ/ngày), hoàn tồn kho và chặn trả trùng phiếu đã trả (T1).
6. `test_06_quan_ly_no_va_dong_tien_phat`: Kiểm tra cập nhật phạt tự động, khóa quyền mượn khi nợ phạt và mở khóa sau khi thanh toán.
7. `test_07_thong_ke_top_5_sach`: Kiểm tra truy vấn thống kê Top 5 sách mượn nhiều nhất.

### Kết quả & Kết luận
* Toàn bộ 7 nhóm ca kiểm thử chạy trên CSDL cô lập đều đạt trạng thái **OK (Passed)**.
* Các chức năng nghiệp vụ giữa 6 thành viên tích hợp đồng bộ trên cùng một tệp `thuvien.db`.
