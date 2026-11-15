import os
from contextlib import closing
from database import DB_PATH, get_connection
from seed_data import seed_database
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

    so_phieu = cap_nhat_tien_phat(db_path=DB_PATH)
    print(f"=> Đã cập nhật phạt cho {so_phieu} phiếu đang quá hạn.")
    return mssv


def xem_sach_va_doc_gia():
    with closing(get_connection(DB_PATH)) as conn:
        ds_doc_gia = conn.execute(
            "SELECT MaDocGia, HoTen, Email FROM DocGia ORDER BY MaDocGia"
        ).fetchall()
        ds_sach = conn.execute(
            "SELECT MaSach, TenSach, TacGia, SoLuongTong, SoLuongCon FROM Sach ORDER BY MaSach"
        ).fetchall()

    print("\n[BẢNG ĐỘC GIẢ]")
    in_bang_sql(
        headers=["MaDocGia", "HoTen", "Email"],
        rows=ds_doc_gia,
        right_align_cols={0},
    )

    print("[BẢNG SÁCH TRONG KHO]")
    in_bang_sql(
        headers=["MaSach", "TenSach", "TacGia", "SoLuongTong", "SoLuongCon"],
        rows=ds_sach,
        right_align_cols={0, 3, 4},
    )


def main():
    mssv_hien_tai = khoi_dong_du_lieu()

    while True:
        print("\n=== HỆ THỐNG QUẢN LÝ THƯ VIỆN ===")
        print("1. Xem danh sách Sách & Độc giả")
        print("2. Kiểm tra điều kiện mượn / Mượn - Trả sách")
        print("3. Đóng tiền phạt")
        print("4. Thống kê Top 5 sách & Tình trạng nợ phạt")
        print("5. Tạo lại dữ liệu mẫu với MSSV khác")
        print("0. Thoát")

        chon = input("Chọn chức năng: ").strip()

        if chon == "1":
            xem_sach_va_doc_gia()
        elif chon == "2":
            ma_dg = int(input("Nhập mã độc giả: "))
            du_dieu_kien, thong_bao = kiem_tra_no_phat(ma_dg, db_path=DB_PATH)
            print(f"=> {thong_bao}")
            if du_dieu_kien:
                print("(Chờ ghép hàm tạo phiếu mượn của TV3 tại đây)")
        elif chon == "3":
            ma_dg = int(input("Nhập mã độc giả cần đóng phạt: "))
            so_phieu = dong_tien_phat(ma_dg, db_path=DB_PATH)
            print(f"=> Đã thanh toán phạt cho {so_phieu} phiếu." if so_phieu else "=> Độc giả này không có nợ phạt.")
        elif chon == "4":
            hien_thi_bao_cao_mssv(mssv_hien_tai, db_path=DB_PATH)
        elif chon == "5":
            mssv_hien_tai = khoi_dong_du_lieu(tao_lai=True)
        elif chon == "0":
            print("Đã thoát chương trình.")
            break
        else:
            print("Lựa chọn không hợp lệ, vui lòng nhập số từ 0 đến 5.")


if __name__ == "__main__":
    main()