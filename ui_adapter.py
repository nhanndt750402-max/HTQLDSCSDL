"""ui_adapter.py — Cầu nối nghiệp vụ TV1–TV4 cho giao diện Tkinter của TV5."""

import os
from datetime import date

from database import DB_PATH
from seed_data import seed_database
import sql as tv2
import business_logic as tv3
import advanced_logic1 as tv4


def khoi_tao_du_lieu(mssv="056207003633", tao_lai=False):
    """Đảm bảo CSDL đã tồn tại, đánh index và cập nhật tiền phạt mới nhất."""
    if tao_lai and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    da_tao_moi = False
    if not os.path.exists(DB_PATH):
        seed_database(mssv.strip() or "056207003633", db_path=DB_PATH)
        da_tao_moi = True

    tv2.tao_index()
    so_phieu_tre = tv4.cap_nhat_tien_phat(db_path=DB_PATH)
    return da_tao_moi, so_phieu_tre


# ---------------------------------------------------------------------------
# Dữ liệu hiển thị bảng (list[dict] cho Treeview)
# ---------------------------------------------------------------------------
def danh_sach_sach():
    return [
        {
            "MaSach": r[0],
            "TenSach": r[1],
            "TacGia": r[2],
            "SoLuongTong": r[3],
            "SoLuongCon": r[4],
        }
        for r in tv2.doc_sach()
    ]


def danh_sach_doc_gia():
    rows = []
    for ma_dg, ho_ten, email in tv2.doc_doc_gia():
        du_dk, thong_bao = tv4.kiem_tra_no_phat(ma_dg, db_path=DB_PATH)
        rows.append(
            {
                "MaDocGia": ma_dg,
                "HoTen": ho_ten,
                "Email": email,
                "TrangThai": "Đủ điều kiện mượn" if du_dk else thong_bao,
            }
        )
    return rows


def danh_sach_phieu_dang_muon():
    return [
        {
            "MaPhieu": r[0],
            "MaDG": r[1],
            "HoTen": r[2],
            "MaSach": r[3],
            "TenSach": r[4],
            "NgayMuon": r[5],
            "HanTra": r[6],
            "SoNgayTre": r[7],
        }
        for r in tv3.lay_phieu_dang_muon(db_path=DB_PATH)
    ]


def danh_sach_phieu_tre():
    tv4.cap_nhat_tien_phat(db_path=DB_PATH)
    hom_nay = date.today().isoformat()
    return [
        {
            "MaPhieu": r[0],
            "HoTen": r[1],
            "TenSach": r[2],
            "NgayMuon": r[3],
            "HanTra": r[4],
        }
        for r in tv2.lay_ds_phieu_tre_han(hom_nay)
    ]


def top_sach_muon(n=5):
    return [
        {
            "Hang": idx,
            "MaSach": r[0],
            "TenSach": r[1],
            "TacGia": r[2],
            "SoLanMuon": r[3],
        }
        for idx, r in enumerate(tv4.top_5_sach(db_path=DB_PATH)[:n], 1)
    ]


# ---------------------------------------------------------------------------
# Thao tác nghiệp vụ trả về (ok: bool, message: str)
# ---------------------------------------------------------------------------
def muon_sach(ma_dg, ma_sach):
    try:
        kq = tv3.muon_sach(ma_dg, ma_sach, db_path=DB_PATH)
        return (
            True,
            f"Mượn thành công!\n"
            f"- Mã phiếu: #{kq.ma_phieu}\n"
            f"- Độc giả: {kq.ho_ten} (ID: {kq.ma_doc_gia})\n"
            f"- Sách: {kq.ten_sach} (Còn trong kho: {kq.so_luong_con})\n"
            f"- Hạn trả: {kq.han_tra}",
        )
    except tv3.LoiNghiepVu as e:
        return False, str(e)


def tra_sach(ma_phieu):
    try:
        kq = tv3.tra_sach(ma_phieu, db_path=DB_PATH)
        phat_msg = (
            f"\n- Trễ {kq.so_ngay_tre} ngày -> Tiền phạt: {kq.tien_phat:,} VNĐ"
            if kq.tien_phat > 0
            else "\n- Trả đúng hạn (Không phạt)"
        )
        return (
            True,
            f"Trả sách '{kq.ten_sach}' thành công!{phat_msg}\n"
            f"- Tồn kho hiện tại: {kq.so_luong_con}",
        )
    except tv3.LoiNghiepVu as e:
        return False, str(e)


def dong_tien_phat(ma_dg):
    try:
        ma = int(str(ma_dg).strip())
        if ma <= 0:
            return False, "Mã độc giả phải là số nguyên dương."
    except ValueError:
        return False, "Mã độc giả phải là số nguyên."

    so_phieu = tv4.dong_tien_phat(ma, db_path=DB_PATH)
    if so_phieu > 0:
        return True, f"Đã thanh toán tiền phạt cho {so_phieu} phiếu của độc giả ID {ma}."
    return False, f"Độc giả ID {ma} không có khoản phạt nào chưa đóng."


def them_doc_gia(ho_ten, email):
    ho_ten, email = ho_ten.strip(), email.strip()
    if not ho_ten or not email:
        return False, "Vui lòng nhập đầy đủ Họ tên và Email."
    if tv2.them_doc_gia(ho_ten, email):
        return True, f"Đã thêm độc giả '{ho_ten}' thành công."
    return False, "Không thể thêm độc giả (Email có thể bị trùng hoặc không hợp lệ)."


def them_sach(ten_sach, tac_gia, so_luong):
    ten_sach, tac_gia = ten_sach.strip(), tac_gia.strip()
    if not ten_sach or not tac_gia:
        return False, "Vui lòng nhập đầy đủ Tên sách và Tác giả."
    try:
        sl = int(str(so_luong).strip())
        if sl <= 0:
            return False, "Số lượng nhập kho phải lớn hơn 0."
    except ValueError:
        return False, "Số lượng phải là số nguyên."

    if tv2.them_sach(ten_sach, tac_gia, sl):
        return True, f"Đã thêm sách '{ten_sach}' (SL: {sl}) thành công."
    return False, "Không thể thêm sách vào CSDL."