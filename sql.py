import sqlite3
from database import get_connection


def doc(sql, params=()):
    """Chạy SELECT, trả về list dòng."""
    conn = get_connection()
    data = conn.execute(sql, params).fetchall()
    conn.close()
    return data


def ghi(sql, params=()):
    """Chạy INSERT/UPDATE/DELETE trong transaction. Trả về True/False."""
    conn = get_connection()
    try:
        conn.execute("BEGIN")
        cur = conn.execute(sql, params)
        if cur.rowcount == 0:
            conn.rollback()
            print("Không tìm thấy dữ liệu cần thao tác")
            return False
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print("Lỗi:", e)
        return False
    finally:
        conn.close()


def them_doc_gia(hoten, email):
    return ghi("INSERT INTO DocGia (HoTen, Email) VALUES (?, ?)", (hoten, email))

def doc_doc_gia():
    return doc("SELECT * FROM DocGia")

def sua_doc_gia(ma_dg, hoten, email):
    return ghi("UPDATE DocGia SET HoTen = ?, Email = ? WHERE MaDocGia = ?", (hoten, email, ma_dg))

def xoa_doc_gia(ma_dg):
    return ghi("DELETE FROM DocGia WHERE MaDocGia = ?", (ma_dg,))


def them_sach(ten_sach, tac_gia, sl_tong):
    return ghi("INSERT INTO Sach (TenSach, TacGia, SoLuongTong, SoLuongCon) VALUES (?, ?, ?, ?)",
               (ten_sach, tac_gia, sl_tong, sl_tong))

def doc_sach():
    return doc("SELECT * FROM Sach")

def sua_sach(ma_sach, ten_sach, tac_gia, sl_tong, sl_con):
    return ghi("UPDATE Sach SET TenSach=?, TacGia=?, SoLuongTong=?, SoLuongCon=? WHERE MaSach=?",
               (ten_sach, tac_gia, sl_tong, sl_con, ma_sach))

def xoa_sach(ma_sach):
    return ghi("DELETE FROM Sach WHERE MaSach = ?", (ma_sach,))


def lay_ds_phieu_tre_han(ngay_hien_tai):
    """Phiếu chưa trả (NgayTraThucTe NULL) và HanTra < ngày hiện tại."""
    return doc("""
        SELECT p.MaPhieuMuon, d.HoTen, s.TenSach, p.NgayMuon, p.HanTra
        FROM PhieuMuon p
        JOIN DocGia d ON p.MaDocGia = d.MaDocGia
        JOIN Sach s ON p.MaSach = s.MaSach
        WHERE p.NgayTraThucTe IS NULL AND p.HanTra < ?
    """, (ngay_hien_tai,))

def lay_lich_su_muon(ma_dg):
    return doc("""
        SELECT p.MaPhieuMuon, s.TenSach, p.NgayMuon, p.HanTra, p.NgayTraThucTe, p.TienPhat
        FROM PhieuMuon p JOIN Sach s ON p.MaSach = s.MaSach
        WHERE p.MaDocGia = ? ORDER BY p.NgayMuon DESC
    """, (ma_dg,))

def lay_ds_no_phat():
    return doc("""
        SELECT d.MaDocGia, d.HoTen, SUM(p.TienPhat) AS TongNo
        FROM DocGia d JOIN PhieuMuon p ON d.MaDocGia = p.MaDocGia
        WHERE p.TienPhat > 0 AND p.DaDongPhat = 0
        GROUP BY d.MaDocGia, d.HoTen
    """)


def tao_index():
    conn = get_connection()
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pm_docgia ON PhieuMuon (MaDocGia)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pm_sach ON PhieuMuon (MaSach)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pm_tra_han ON PhieuMuon (NgayTraThucTe, HanTra)")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    tao_index()