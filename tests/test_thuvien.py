import os
import sys
import tempfile
import unittest
from datetime import date

# Đảm bảo import được các module ở thư mục gốc dự án
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import database
import sql
import business_logic as bl
import advanced_logic1 as adv
from seed_data import seed_database


class TestThuVien(unittest.TestCase):
    """Bộ kiểm thử tích hợp (Integration & Unit Test) cho Hệ thống Quản lý Thư viện."""

    def setUp(self):
        """Tạo CSDL SQLite tạm thời sạch trước mỗi test case."""
        fd, self.test_db = tempfile.mkstemp(prefix="test_tv_", suffix=".db")
        os.close(fd)
        os.remove(self.test_db)  # Để seed_database tự khởi tạo schema mới

        # Chuyển hướng kết nối của sql.py (TV2) sang CSDL tạm
        self._orig_sql_conn = sql.get_connection
        sql.get_connection = lambda db_path=self.test_db: database.get_connection(self.test_db)

        seed_database("056207003633", db_path=self.test_db)

    def tearDown(self):
        """Khôi phục kết nối và xóa CSDL tạm sau mỗi test case."""
        sql.get_connection = self._orig_sql_conn
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    # 1. Kiểm thử TV1: Khởi tạo dữ liệu & chống ghi đè
    def test_01_khoi_tao_du_lieu_va_chong_ghi_de(self):
        ds_dg = sql.doc_doc_gia()
        ds_sach = sql.doc_sach()
        self.assertEqual(len(ds_dg), 6)
        self.assertGreaterEqual(len(ds_sach), 6)

        with self.assertRaises(ValueError):
            seed_database("056207003633", db_path=self.test_db)

    # 2. Kiểm thử TV2: CRUD Độc giả & Sách
    def test_02_crud_doc_gia_va_sach(self):
        self.assertTrue(sql.them_doc_gia("Độc Giả Test", "test_dg@example.com"))
        ds_dg = sql.doc_doc_gia()
        ma_dg_moi = ds_dg[-1][0]
        self.assertTrue(sql.sua_doc_gia(ma_dg_moi, "Độc Giả Đã Sửa", "sua_dg@example.com"))

        self.assertTrue(sql.them_sach("Sách Kiểm Thử", "Tác Giả QA", 3))
        ds_sach = sql.doc_sach()
        ma_sach_moi = ds_sach[-1][0]
        self.assertTrue(sql.sua_sach(ma_sach_moi, "Sách Kiểm Thử V2", "Tác Giả QA", 5, 5))

        # Xóa bản ghi vừa tạo (chưa có phiếu mượn ràng buộc)
        self.assertTrue(sql.xoa_doc_gia(ma_dg_moi))
        self.assertTrue(sql.xoa_sach(ma_sach_moi))

    # 3. Kiểm thử TV3: Mượn sách thành công & trừ tồn kho
    def test_03_muon_sach_thanh_cong(self):
        sql.them_doc_gia("Nguyễn Văn Test", "nvtest@example.com")
        ma_dg = sql.doc_doc_gia()[-1][0]

        sql.them_sach("Lập Trình Python Nâng Cao", "Guido", 2)
        ma_sach = sql.doc_sach()[-1][0]

        kq = bl.muon_sach(ma_dg, ma_sach, ngay_muon="2026-11-01", db_path=self.test_db)
        self.assertEqual(kq.ma_doc_gia, ma_dg)
        self.assertEqual(kq.ma_sach, ma_sach)
        self.assertEqual(kq.han_tra, "2026-11-15")
        self.assertEqual(kq.so_luong_con, 1)

    # 4. Kiểm thử TV3: Các quy tắc chặn mượn (R2 - R6)
    def test_04_chan_muon_vi_pham_quy_tac(self):
        sql.them_doc_gia("Độc Giả A", "dga@example.com")
        sql.them_doc_gia("Độc Giả B", "dgb@example.com")
        ds_dg = sql.doc_doc_gia()
        dg_a, dg_b = ds_dg[-2][0], ds_dg[-1][0]

        sql.them_sach("Sách 1", "TG 1", 2)
        sql.them_sach("Sách 2", "TG 2", 1)
        sql.them_sach("Sách 3", "TG 3", 2)
        sql.them_sach("Sách 4", "TG 4", 2)
        ds_sach = sql.doc_sach()
        s1, s2, s3, s4 = [r[0] for r in ds_sach[-4:]]

        # Mượn Sách 1 thành công
        bl.muon_sach(dg_a, s1, ngay_muon="2026-11-01", db_path=self.test_db)

        # R5: Mượn trùng đầu sách đang giữ -> DaMuonSachNay
        with self.assertRaises(bl.DaMuonSachNay):
            bl.muon_sach(dg_a, s1, ngay_muon="2026-11-01", db_path=self.test_db)

        # Mượn Sách 2 (chỉ có 1 cuốn) -> hết tồn kho
        bl.muon_sach(dg_a, s2, ngay_muon="2026-11-01", db_path=self.test_db)

        # R6: Độc giả B mượn Sách 2 đã hết -> HetSach
        with self.assertRaises(bl.HetSach):
            bl.muon_sach(dg_b, s2, ngay_muon="2026-11-01", db_path=self.test_db)

        # R4: Độc giả A mượn cuốn thứ 3 rồi thử mượn cuốn thứ 4 -> VuotGioiHanMuon
        bl.muon_sach(dg_a, s3, ngay_muon="2026-11-01", db_path=self.test_db)
        with self.assertRaises(bl.VuotGioiHanMuon):
            bl.muon_sach(dg_a, s4, ngay_muon="2026-11-01", db_path=self.test_db)

    # 5. Kiểm thử TV3: Trả sách đúng hạn, trễ hạn & chặn trả 2 lần
    def test_05_tra_sach_va_tinh_phat(self):
        sql.them_doc_gia("Độc Giả Trả Sách", "trasach@example.com")
        ma_dg = sql.doc_doc_gia()[-1][0]

        sql.them_sach("Sách Trả", "TG Trả", 2)
        ma_sach = sql.doc_sach()[-1][0]

        # Mượn ngày 01/11 -> Hạn trả 15/11
        kq_muon = bl.muon_sach(ma_dg, ma_sach, ngay_muon="2026-11-01", db_path=self.test_db)

        # Trả trễ 4 ngày (19/11) -> Phạt 4 * 5,000 = 20,000 VNĐ, tồn kho hoàn về 2
        kq_tra = bl.tra_sach(kq_muon.ma_phieu, ngay_tra="2026-11-19", db_path=self.test_db)
        self.assertEqual(kq_tra.so_ngay_tre, 4)
        self.assertEqual(kq_tra.tien_phat, 20000)
        self.assertEqual(kq_tra.so_luong_con, 2)

        # Trả lại phiếu đã trả -> PhieuDaTra
        with self.assertRaises(bl.PhieuDaTra):
            bl.tra_sach(kq_muon.ma_phieu, ngay_tra="2026-11-20", db_path=self.test_db)

    # 6. Kiểm thử TV4: Cập nhật phạt tự động, kiểm tra nợ phạt & đóng tiền phạt
    def test_06_quan_ly_no_va_dong_tien_phat(self):
        sql.them_doc_gia("Độc Giả Nợ Phạt", "nophat@example.com")
        ma_dg = sql.doc_doc_gia()[-1][0]

        sql.them_sach("Sách Phạt", "TG Phạt", 3)
        ma_sach = sql.doc_sach()[-1][0]

        # Mượn ngày 01/11 -> Hạn trả 15/11
        bl.muon_sach(ma_dg, ma_sach, ngay_muon="2026-11-01", db_path=self.test_db)

        # Giả lập đến ngày 18/11 (trễ 3 ngày = 15,000 VNĐ)
        adv.cap_nhat_tien_phat(db_path=self.test_db, as_of=date(2026, 11, 18))
        du_dk, msg = adv.kiem_tra_no_phat(ma_dg, db_path=self.test_db)
        self.assertFalse(du_dk)
        self.assertIn("15,000", msg)

        # Đóng tiền phạt -> Đủ điều kiện trở lại
        so_phieu_da_dong = adv.dong_tien_phat(ma_dg, db_path=self.test_db)
        self.assertEqual(so_phieu_da_dong, 1)

        du_dk_sau, _ = adv.kiem_tra_no_phat(ma_dg, db_path=self.test_db)
        self.assertTrue(du_dk_sau)

    # 7. Kiểm thử TV4: Thống kê Top 5 sách
    def test_07_thong_ke_top_5_sach(self):
        top = adv.top_5_sach(db_path=self.test_db)
        self.assertLessEqual(len(top), 5)
        if len(top) >= 2:
            # Đảm bảo sắp xếp giảm dần theo số lượt mượn
            self.assertGreaterEqual(top[0][3], top[1][3])


if __name__ == "__main__":
    unittest.main(verbosity=2)