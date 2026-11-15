"""Xử lý logic nâng cao: Tính phạt trễ hạn, kiểm tra nợ phạt và thống kê."""

from contextlib import closing
from datetime import date

from database import DB_PATH, get_connection


def in_bang_sql(headers, rows, right_align_cols=None):
    """Hiển thị dữ liệu theo định dạng bảng viền chuẩn giao diện dòng lệnh SQL."""
    right_align_cols = set(right_align_cols or [])
    str_rows = [[str(cell) for cell in row] for row in rows]
    col_widths = [len(str(h)) for h in headers]

    for row in str_rows:
        for i, cell in enumerate(row):
            if len(cell) > col_widths[i]:
                col_widths[i] = len(cell)

    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    def format_row(row_items):
        cells = []
        for i, item in enumerate(row_items):
            if i in right_align_cols:
                cells.append(f" {item:>{col_widths[i]}} ")
            else:
                cells.append(f" {item:<{col_widths[i]}} ")
        return "|" + "|".join(cells) + "|"

    print(separator)
    print(format_row(headers))
    print(separator)
    if not str_rows:
        empty_msg = "(Không có dữ liệu)"
        total_inner_width = len(separator) - 2
        print(f"| {empty_msg:<{total_inner_width - 2}} |")
    else:
        for row in str_rows:
            print(format_row(row))
    print(separator)
    print(f"({len(str_rows)} rows)\n")


def cap_nhat_tien_phat(db_path=DB_PATH, muc_phat_ngay=5000, as_of=None):
    """Quét các phiếu chưa trả và đã quá hạn để cập nhật tiền phạt mới nhất."""
    hom_nay = as_of or date.today()
    hom_nay_str = hom_nay.isoformat()

    with closing(get_connection(db_path)) as conn, conn:
        danh_sach_tre = conn.execute(
            """
            SELECT MaPhieuMuon, HanTra
            FROM PhieuMuon
            WHERE NgayTraThucTe IS NULL AND HanTra < ?
            """,
            (hom_nay_str,),
        ).fetchall()

        for ma_phieu, han_tra_str in danh_sach_tre:
            han_tra = date.fromisoformat(han_tra_str)
            so_ngay_tre = (hom_nay - han_tra).days
            tien_phat = so_ngay_tre * muc_phat_ngay

            conn.execute(
                "UPDATE PhieuMuon SET TienPhat = ? WHERE MaPhieuMuon = ?",
                (tien_phat, ma_phieu),
            )
    return len(danh_sach_tre)


def kiem_tra_no_phat(ma_doc_gia, db_path=DB_PATH):
    """Kiểm tra độc giả có khoản phạt nào chưa đóng (DaDongPhat = 0) hay không."""
    with closing(get_connection(db_path)) as conn:
        row = conn.execute(
            """
            SELECT D.HoTen, COALESCE(SUM(P.TienPhat), 0)
            FROM DocGia D
            LEFT JOIN PhieuMuon P
                ON D.MaDocGia = P.MaDocGia AND P.DaDongPhat = 0
            WHERE D.MaDocGia = ?
            GROUP BY D.MaDocGia, D.HoTen
            """,
            (ma_doc_gia,),
        ).fetchone()

    if row is None:
        return False, f"Không tìm thấy độc giả có mã {ma_doc_gia}."

    ho_ten, tong_no = row
    if tong_no > 0:
        return False, f"Độc giả {ho_ten} (Mã: {ma_doc_gia}) đang nợ {tong_no:,} VNĐ. Cần đóng phạt trước khi mượn!"
    return True, f"Độc giả {ho_ten} (Mã: {ma_doc_gia}) đủ điều kiện mượn sách."


def dong_tien_phat(ma_doc_gia, db_path=DB_PATH):
    """Cập nhật trạng thái đã đóng phạt cho toàn bộ phiếu nợ của độc giả."""
    with closing(get_connection(db_path)) as conn, conn:
        cursor = conn.execute(
            """
            UPDATE PhieuMuon
            SET DaDongPhat = 1
            WHERE MaDocGia = ? AND TienPhat > 0 AND DaDongPhat = 0
            """,
            (ma_doc_gia,),
        )
    return cursor.rowcount


def top_5_sach(db_path=DB_PATH):
    """Thống kê Top 5 sách được mượn nhiều nhất."""
    with closing(get_connection(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT S.MaSach, S.TenSach, S.TacGia, COUNT(P.MaPhieuMuon) AS SoLanMuon
            FROM Sach S
            JOIN PhieuMuon P ON S.MaSach = P.MaSach
            GROUP BY S.MaSach, S.TenSach, S.TacGia
            ORDER BY SoLanMuon DESC, S.MaSach ASC
            LIMIT 5
            """
        ).fetchall()
    return rows


def hien_thi_bao_cao_mssv(mssv=None, db_path=DB_PATH):
    """In danh sách độc giả và Top 5 sách dưới dạng bảng chuẩn SQL."""
    with closing(get_connection(db_path)) as conn:
        ds_doc_gia = conn.execute(
            "SELECT MaDocGia, HoTen FROM DocGia ORDER BY MaDocGia ASC"
        ).fetchall()

    nhan_mssv = f" (MSSV: {mssv})" if mssv else ""
    print(f"\n[BẢNG 1] KIỂM TRA NỢ PHẠT ĐỘC GIẢ{nhan_mssv}")
    rows_no_phat = []
    for ma_dg, ho_ten in ds_doc_gia:
        du_dieu_kien, thong_bao = kiem_tra_no_phat(ma_dg, db_path)
        if du_dieu_kien:
            tien_no = "0"
            trang_thai = "Đủ điều kiện mượn sách"
        elif "đang nợ " in thong_bao:
            tien_no = thong_bao.split("đang nợ ")[1].split(" VNĐ")[0]
            trang_thai = "Cần đóng phạt trước khi mượn!"
        else:
            tien_no = "-"
            trang_thai = thong_bao
        rows_no_phat.append([ma_dg, ho_ten, tien_no, trang_thai])

    in_bang_sql(
        headers=["MaDocGia", "HoTen", "TienNo (VND)", "TrangThai"],
        rows=rows_no_phat,
        right_align_cols={0, 2},
    )

    print(f"[BẢNG 2] TOP 5 SÁCH ĐƯỢC MƯỢN NHIỀU NHẤT{nhan_mssv}")
    ds_top_sach = top_5_sach(db_path)
    in_bang_sql(
        headers=["MaSach", "TenSach", "TacGia", "SoLanMuon"],
        rows=ds_top_sach,
        right_align_cols={0, 3},
    )


if __name__ == "__main__":
    cap_nhat_tien_phat()
    hien_thi_bao_cao_mssv()