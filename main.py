import os
from datetime import date
from database import DB_PATH
from seed_data import seed_database
from sql import (
    doc_doc_gia,
    doc_sach,
    lay_ds_phieu_tre_han,
    lay_lich_su_muon,
    sua_doc_gia,
    sua_sach,
    tao_index,
    them_doc_gia,
    them_sach,
    xoa_doc_gia,
    xoa_sach,
)
from advanced_logic1 import (
    cap_nhat_tien_phat,
    dong_tien_phat,
    hien_thi_bao_cao_mssv,
    in_bang_sql,
    kiem_tra_no_phat,
)


def khoi_dong_du_lieu(tao_lai=False):
    if tao_lai and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    mssv = None
    if not os.path.exists(DB_PATH):
        mssv = input("Nhập MSSV để khởi tạo dữ liệu hệ thống: ").strip()
        seed_database(mssv, db_path=DB_PATH)
        print(f"=> Đã tạo dữ liệu mẫu theo MSSV {mssv} vào {DB_PATH}.")
    else:
        print(f"=> Đã tải dữ liệu sẵn có từ {DB_PATH}.")

    tao_index()
    so_phieu = cap_nhat_tien_phat(db_path=DB_PATH)
    print(f"=> Đã cập nhật phạt cho {so_phieu} phiếu đang quá hạn.")
    return mssv


def xem_sach_va_doc_gia():
    print("\n[BẢNG ĐỘC GIẢ]")
    in_bang_sql(
        headers=["MaDocGia", "HoTen", "Email"],
        rows=doc_doc_gia(),
        right_align_cols={0},
    )

    print("[BẢNG SÁCH TRONG KHO]")
    in_bang_sql(
        headers=["MaSach", "TenSach", "TacGia", "SoLuongTong", "SoLuongCon"],
        rows=doc_sach(),
        right_align_cols={0, 3, 4},
    )


def quan_ly_doc_gia():
    while True:
        print("\n--- QUẢN LÝ ĐỘC GIẢ ---")
        print("1. Xem danh sách độc giả")
        print("2. Thêm độc giả mới")
        print("3. Sửa thông tin độc giả")
        print("4. Xóa độc giả")
        print("5. Xem lịch sử mượn của độc giả")
        print("0. Quay lại")
        chon = input("Chọn: ").strip()

        if chon == "1":
            in_bang_sql(["MaDocGia", "HoTen", "Email"], doc_doc_gia(), right_align_cols={0})
        elif chon == "2":
            ten = input("Họ tên: ").strip()
            email = input("Email: ").strip()
            if them_doc_gia(ten, email):
                print("=> Đã thêm độc giả thành công.")
        elif chon == "3":
            ma = int(input("Mã độc giả cần sửa: "))
            ten = input("Họ tên mới: ").strip()
            email = input("Email mới: ").strip()
            if sua_doc_gia(ma, ten, email):
                print("=> Đã cập nhật thông tin độc giả.")
        elif chon == "4":
            ma = int(input("Mã độc giả cần xóa: "))
            if xoa_doc_gia(ma):
                print("=> Đã xóa độc giả.")
        elif chon == "5":
            ma = int(input("Nhập mã độc giả: "))
            lich_su = lay_lich_su_muon(ma)
            in_bang_sql(
                headers=["MaPhieu", "TenSach", "NgayMuon", "HanTra", "NgayTraThucTe", "TienPhat"],
                rows=[[r[0], r[1], r[2], r[3], r[4] or "Chưa trả", f"{r[5]:,}"] for r in lich_su],
                right_align_cols={0, 5},
            )
        elif chon == "0":
            break


def quan_ly_sach():
    while True:
        print("\n--- QUẢN LÝ SÁCH ---")
        print("1. Xem danh mục sách")
        print("2. Thêm sách mới")
        print("3. Sửa thông tin sách")
        print("4. Xóa sách")
        print("0. Quay lại")
        chon = input("Chọn: ").strip()

        if chon == "1":
            in_bang_sql(
                ["MaSach", "TenSach", "TacGia", "SoLuongTong", "SoLuongCon"],
                doc_sach(),
                right_align_cols={0, 3, 4},
            )
        elif chon == "2":
            ten = input("Tên sách: ").strip()
            tac_gia = input("Tác giả: ").strip()
            sl = int(input("Số lượng nhập kho: "))
            if sl <= 0:
                print("=> Số lượng phải lớn hơn 0.")
            elif them_sach(ten, tac_gia, sl):
                print("=> Đã thêm sách thành công.")
        elif chon == "3":
            ma = int(input("Mã sách cần sửa: "))
            ten = input("Tên sách mới: ").strip()
            tac_gia = input("Tác giả mới: ").strip()
            sl_tong = int(input("Số lượng tổng mới: "))
            sl_con = int(input("Số lượng còn mới: "))
            if sl_con < 0 or sl_con > sl_tong:
                print("=> Lỗi: Số lượng còn phải nằm trong khoảng từ 0 đến số lượng tổng.")
            elif sua_sach(ma, ten, tac_gia, sl_tong, sl_con):
                print("=> Đã cập nhật thông tin sách.")
        elif chon == "4":
            ma = int(input("Mã sách cần xóa: "))
            if xoa_sach(ma):
                print("=> Đã xóa sách.")
        elif chon == "0":
            break


def main():
    mssv_hien_tai = khoi_dong_du_lieu()

    while True:
        print("\n=== HỆ THỐNG QUẢN LÝ THƯ VIỆN ===")
        print("1. Xem danh sách Sách & Độc giả")
        print("2. Quản lý Độc giả (Thêm / Sửa / Xóa / Lịch sử mượn)")
        print("3. Quản lý Sách (Thêm / Sửa / Xóa)")
        print("4. Kiểm tra điều kiện mượn / Mượn - Trả sách")
        print("5. Đóng tiền phạt")
        print("6. Thống kê Top 5 sách, Nợ phạt & Phiếu trễ hạn")
        print("7. Tạo lại dữ liệu mẫu với MSSV khác")
        print("0. Thoát")

        chon = input("Chọn chức năng: ").strip()

        if chon == "1":
            xem_sach_va_doc_gia()
        elif chon == "2":
            quan_ly_doc_gia()
        elif chon == "3":
            quan_ly_sach()
        elif chon == "4":
            ma_dg = int(input("Nhập mã độc giả: "))
            du_dieu_kien, thong_bao = kiem_tra_no_phat(ma_dg, db_path=DB_PATH)
            print(f"=> {thong_bao}")
            if du_dieu_kien:
                print("(Chờ ghép hàm tạo phiếu mượn của TV3 tại đây)")
        elif chon == "5":
            ma_dg = int(input("Nhập mã độc giả cần đóng phạt: "))
            so_phieu = dong_tien_phat(ma_dg, db_path=DB_PATH)
            print(f"=> Đã thanh toán phạt cho {so_phieu} phiếu." if so_phieu else "=> Độc giả này không có nợ phạt.")
        elif chon == "6":
            hien_thi_bao_cao_mssv(mssv_hien_tai, db_path=DB_PATH)
            print("[BẢNG 3] DANH SÁCH PHIẾU ĐANG TRỄ HẠN")
            ds_tre = lay_ds_phieu_tre_han(date.today().isoformat())
            in_bang_sql(
                headers=["MaPhieu", "HoTen", "TenSach", "NgayMuon", "HanTra"],
                rows=ds_tre,
                right_align_cols={0},
            )
        elif chon == "7":
            mssv_hien_tai = khoi_dong_du_lieu(tao_lai=True)
        elif chon == "0":
            print("Đã thoát chương trình.")
            break
        else:
            print("Lựa chọn không hợp lệ, vui lòng nhập số từ 0 đến 7.")


if __name__ == "__main__":
    main()
