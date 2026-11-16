"""
business_logic.py — Nghiệp vụ cốt lõi Mượn / Trả sách.

Phụ trách : Thành viên 3 (TV3) — Core Logic.
Phụ thuộc : database.py (TV1) — get_connection, DB_PATH.
Người dùng: main.py (TV5) gọi các hàm public bên dưới; tests/ (TV6) kiểm thử.

Hàm public
----------
    muon_sach(ma_doc_gia, ma_sach, ...)   -> KetQuaMuon
    tra_sach(ma_phieu, ...)               -> KetQuaTra
    lay_phieu_dang_muon(ma_doc_gia=None)  -> list[tuple]
    tinh_so_ngay_tre(han_tra, ngay_tra)   -> int
    tinh_tien_phat(han_tra, ngay_tra)     -> int

Quy tắc nghiệp vụ (áp dụng khi MƯỢN)
-----------------------------------
    R1. Độc giả và sách phải tồn tại.
    R2. Độc giả không còn khoản phạt chưa đóng (TienPhat > 0 AND DaDongPhat = 0)
        — cùng điều kiện với advanced_logic1.kiem_tra_no_phat (TV4).
    R3. Độc giả không giữ cuốn nào đã quá hạn mà chưa trả
        (chặn ngay cả khi cap_nhat_tien_phat chưa được chạy).
    R4. Số phiếu đang mượn < GIOI_HAN_MUON.
    R5. Không mượn trùng một đầu sách đang giữ.
    R6. Sách còn tồn (SoLuongCon > 0).
    Thỏa hết -> trừ tồn 1 cuốn + tạo phiếu, trong CÙNG một transaction.

Quy tắc khi TRẢ
---------------
    T1. Phiếu phải tồn tại và chưa trả.
    T2. Ngày trả >= ngày mượn.
    T3. Ghi NgayTraThucTe, tính TienPhat = (NgayTraThucTe - HanTra) * MUC_PHAT_NGAY
        (chỉ khi > 0), cộng lại 1 cuốn vào kho — cùng một transaction.

Tính toàn vẹn
-------------
Mọi thao tác ghi chạy trong `BEGIN IMMEDIATE ... COMMIT`; có lỗi -> `ROLLBACK`,
CSDL giữ nguyên trạng thái trước đó. BEGIN IMMEDIATE giữ khóa ghi ngay từ đầu nên
hai lượt mượn đồng thời không thể cùng lấy cuốn sách cuối cùng.

Lỗi nghiệp vụ được báo bằng exception (lớp con của LoiNghiepVu) để giao diện
tự quyết định cách hiển thị; module này KHÔNG print.
"""

from __future__ import annotations

from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import date, timedelta

from database import DB_PATH, get_connection

# ---------------------------------------------------------------------------
# Tham số nghiệp vụ (đổi tại đây, không rải số cứng trong code)
# ---------------------------------------------------------------------------
GIOI_HAN_MUON = 3            # Số phiếu tối đa một độc giả được giữ cùng lúc
SO_NGAY_MUON_MAC_DINH = 14   # Hạn mượn, khớp với dữ liệu mẫu seed_data (TV1)
MUC_PHAT_NGAY = 5000         # VNĐ/ngày, khớp cap_nhat_tien_phat (TV4) và seed_data


# ---------------------------------------------------------------------------
# Exception nghiệp vụ
# ---------------------------------------------------------------------------
class LoiNghiepVu(Exception):
    """Lớp cha cho mọi lỗi nghiệp vụ mượn/trả. Thông điệp đã sẵn để hiển thị."""


class KhongTimThay(LoiNghiepVu):
    """Độc giả / sách / phiếu mượn không tồn tại."""


class DuLieuKhongHopLe(LoiNghiepVu):
    """Tham số đầu vào sai định dạng hoặc vô nghĩa (ngày sai, số âm...)."""


class ConNoPhat(LoiNghiepVu):
    """R2/R3: độc giả còn nợ phạt hoặc đang giữ sách quá hạn."""


class VuotGioiHanMuon(LoiNghiepVu):
    """R4: đã giữ đủ GIOI_HAN_MUON cuốn."""


class DaMuonSachNay(LoiNghiepVu):
    """R5: đang giữ một cuốn cùng đầu sách."""


class HetSach(LoiNghiepVu):
    """R6: sách đã hết trong kho."""


class PhieuDaTra(LoiNghiepVu):
    """T1: phiếu đã được trả trước đó."""


# ---------------------------------------------------------------------------
# Kết quả trả về cho giao diện
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class KetQuaMuon:
    ma_phieu: int
    ma_doc_gia: int
    ho_ten: str
    ma_sach: int
    ten_sach: str
    ngay_muon: str
    han_tra: str
    so_luong_con: int  # tồn kho SAU khi mượn


@dataclass(frozen=True)
class KetQuaTra:
    ma_phieu: int
    ma_doc_gia: int
    ma_sach: int
    ten_sach: str
    han_tra: str
    ngay_tra: str
    so_ngay_tre: int
    tien_phat: int
    so_luong_con: int  # tồn kho SAU khi trả


# ---------------------------------------------------------------------------
# Tiện ích nội bộ
# ---------------------------------------------------------------------------
def _chuan_hoa_ngay(gia_tri, ten_truong: str) -> date:
    """Nhận date / chuỗi 'YYYY-MM-DD' / None (= hôm nay) và trả về date."""
    if gia_tri is None:
        return date.today()
    if isinstance(gia_tri, date):
        return gia_tri
    try:
        return date.fromisoformat(str(gia_tri).strip())
    except ValueError:
        raise DuLieuKhongHopLe(
            f"{ten_truong} '{gia_tri}' không hợp lệ, cần định dạng YYYY-MM-DD."
        ) from None


def _chuan_hoa_ma(gia_tri, ten_truong: str) -> int:
    """Ép mã về int dương; báo lỗi rõ ràng thay vì để SQLite so sánh sai kiểu."""
    try:
        ma = int(gia_tri)
    except (TypeError, ValueError):
        raise DuLieuKhongHopLe(f"{ten_truong} phải là số nguyên.") from None
    if ma <= 0:
        raise DuLieuKhongHopLe(f"{ten_truong} phải lớn hơn 0.")
    return ma


@contextmanager
def _giao_dich(db_path):
    """
    Mở kết nối và chạy khối lệnh trong một transaction tường minh.

    isolation_level=None tắt cơ chế tự BEGIN của sqlite3 để chính ta điều khiển
    BEGIN IMMEDIATE / COMMIT / ROLLBACK (yêu cầu toàn vẹn dữ liệu trong PDF).
    """
    with closing(get_connection(db_path)) as conn:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")


# ---------------------------------------------------------------------------
# Tính trễ hạn / tiền phạt (hàm thuần, không đụng CSDL)
# ---------------------------------------------------------------------------
def tinh_so_ngay_tre(han_tra, ngay_tra) -> int:
    """Số ngày trễ = NgayTraThucTe - HanTra, không âm."""
    han = _chuan_hoa_ngay(han_tra, "Hạn trả")
    tra = _chuan_hoa_ngay(ngay_tra, "Ngày trả")
    return max(0, (tra - han).days)


def tinh_tien_phat(han_tra, ngay_tra, muc_phat_ngay: int = MUC_PHAT_NGAY) -> int:
    """Tiền phạt = số ngày trễ x mức phạt/ngày."""
    return tinh_so_ngay_tre(han_tra, ngay_tra) * muc_phat_ngay


# ---------------------------------------------------------------------------
# NGHIỆP VỤ MƯỢN SÁCH
# ---------------------------------------------------------------------------
def muon_sach(
    ma_doc_gia,
    ma_sach,
    ngay_muon=None,
    so_ngay_muon: int = SO_NGAY_MUON_MAC_DINH,
    gioi_han_muon: int = GIOI_HAN_MUON,
    db_path=DB_PATH,
) -> KetQuaMuon:
    """
    Tạo phiếu mượn mới sau khi kiểm tra đủ R1–R6 (xem docstring module).

    Raises: KhongTimThay, ConNoPhat, VuotGioiHanMuon, DaMuonSachNay, HetSach,
            DuLieuKhongHopLe.
    """
    ma_doc_gia = _chuan_hoa_ma(ma_doc_gia, "Mã độc giả")
    ma_sach = _chuan_hoa_ma(ma_sach, "Mã sách")
    ngay = _chuan_hoa_ngay(ngay_muon, "Ngày mượn")
    if int(so_ngay_muon) <= 0:
        raise DuLieuKhongHopLe("Số ngày mượn phải lớn hơn 0.")
    han_tra = ngay + timedelta(days=int(so_ngay_muon))
    ngay_iso, han_iso = ngay.isoformat(), han_tra.isoformat()

    with _giao_dich(db_path) as conn:
        # R1 — tồn tại
        doc_gia = conn.execute(
            "SELECT HoTen FROM DocGia WHERE MaDocGia = ?", (ma_doc_gia,)
        ).fetchone()
        if doc_gia is None:
            raise KhongTimThay(f"Không tìm thấy độc giả có mã {ma_doc_gia}.")
        ho_ten = doc_gia[0]

        sach = conn.execute(
            "SELECT TenSach, SoLuongCon FROM Sach WHERE MaSach = ?", (ma_sach,)
        ).fetchone()
        if sach is None:
            raise KhongTimThay(f"Không tìm thấy sách có mã {ma_sach}.")
        ten_sach, _ = sach

        # Gom các chỉ số của độc giả trong MỘT truy vấn
        no_phat, so_qua_han, so_dang_muon, dang_giu_sach_nay = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN TienPhat > 0 AND DaDongPhat = 0
                                  THEN TienPhat END), 0),
                COUNT(CASE WHEN NgayTraThucTe IS NULL AND HanTra < ? THEN 1 END),
                COUNT(CASE WHEN NgayTraThucTe IS NULL THEN 1 END),
                COUNT(CASE WHEN NgayTraThucTe IS NULL AND MaSach = ? THEN 1 END)
            FROM PhieuMuon
            WHERE MaDocGia = ?
            """,
            (ngay_iso, ma_sach, ma_doc_gia),
        ).fetchone()

        # R2 — nợ phạt
        if no_phat > 0:
            raise ConNoPhat(
                f"Độc giả {ho_ten} (Mã: {ma_doc_gia}) đang nợ {no_phat:,} VNĐ. "
                "Cần đóng phạt trước khi mượn!"
            )
        # R3 — đang giữ sách quá hạn
        if so_qua_han > 0:
            raise ConNoPhat(
                f"Độc giả {ho_ten} đang giữ {so_qua_han} cuốn đã quá hạn. "
                "Cần trả sách trước khi mượn tiếp!"
            )
        # R4 — giới hạn
        if so_dang_muon >= gioi_han_muon:
            raise VuotGioiHanMuon(
                f"Độc giả {ho_ten} đang mượn {so_dang_muon}/{gioi_han_muon} cuốn, "
                "đã đạt giới hạn."
            )
        # R5 — trùng đầu sách
        if dang_giu_sach_nay:
            raise DaMuonSachNay(
                f"Độc giả {ho_ten} đang mượn '{ten_sach}' và chưa trả."
            )

        # R6 — trừ tồn có điều kiện: nếu SoLuongCon = 0 thì rowcount = 0
        cur = conn.execute(
            "UPDATE Sach SET SoLuongCon = SoLuongCon - 1 "
            "WHERE MaSach = ? AND SoLuongCon > 0",
            (ma_sach,),
        )
        if cur.rowcount == 0:
            raise HetSach(f"Sách '{ten_sach}' (Mã: {ma_sach}) đã hết trong kho.")

        cur = conn.execute(
            "INSERT INTO PhieuMuon (MaDocGia, MaSach, NgayMuon, HanTra) "
            "VALUES (?, ?, ?, ?)",
            (ma_doc_gia, ma_sach, ngay_iso, han_iso),
        )
        ma_phieu = cur.lastrowid
        so_luong_con = conn.execute(
            "SELECT SoLuongCon FROM Sach WHERE MaSach = ?", (ma_sach,)
        ).fetchone()[0]

    return KetQuaMuon(ma_phieu, ma_doc_gia, ho_ten, ma_sach, ten_sach,
                      ngay_iso, han_iso, so_luong_con)


# ---------------------------------------------------------------------------
# NGHIỆP VỤ TRẢ SÁCH
# ---------------------------------------------------------------------------
def tra_sach(ma_phieu, ngay_tra=None, muc_phat_ngay: int = MUC_PHAT_NGAY,
             db_path=DB_PATH) -> KetQuaTra:
    """
    Ghi nhận trả sách cho một phiếu (T1–T3).

    Về tiền phạt: cap_nhat_tien_phat (TV4) có thể đã ghi TienPhat tạm tính cho
    phiếu chưa trả; khi trả ta ghi đè bằng số CHỐT theo ngày trả thực tế.
    Nếu phiếu đã bị đánh dấu DaDongPhat = 1 trước khi trả (xem báo cáo kiểm tra,
    mục lỗi TV4) mà tiền phạt chốt lớn hơn số đã ghi lúc đóng, phiếu được mở lại
    DaDongPhat = 0 để không thất thu.

    Raises: KhongTimThay, PhieuDaTra, DuLieuKhongHopLe.
    """
    ma_phieu = _chuan_hoa_ma(ma_phieu, "Mã phiếu mượn")
    ngay = _chuan_hoa_ngay(ngay_tra, "Ngày trả")
    ngay_iso = ngay.isoformat()

    with _giao_dich(db_path) as conn:
        phieu = conn.execute(
            """
            SELECT p.MaDocGia, p.MaSach, s.TenSach, p.NgayMuon, p.HanTra,
                   p.NgayTraThucTe, p.TienPhat, p.DaDongPhat
            FROM PhieuMuon p JOIN Sach s ON s.MaSach = p.MaSach
            WHERE p.MaPhieuMuon = ?
            """,
            (ma_phieu,),
        ).fetchone()
        if phieu is None:
            raise KhongTimThay(f"Không tìm thấy phiếu mượn có mã {ma_phieu}.")
        (ma_doc_gia, ma_sach, ten_sach, ngay_muon, han_tra,
         da_tra, phat_cu, da_dong_cu) = phieu

        if da_tra is not None:
            raise PhieuDaTra(f"Phiếu {ma_phieu} đã được trả ngày {da_tra}.")
        if ngay_iso < ngay_muon:
            raise DuLieuKhongHopLe(
                f"Ngày trả {ngay_iso} không thể trước ngày mượn {ngay_muon}."
            )

        so_ngay_tre = tinh_so_ngay_tre(han_tra, ngay)
        tien_phat = so_ngay_tre * muc_phat_ngay
        # Đã đóng đủ số chốt thì giữ trạng thái; ngược lại còn nợ (nếu có phạt)
        da_dong = 1 if (da_dong_cu == 1 and tien_phat <= phat_cu) else 0

        conn.execute(
            "UPDATE PhieuMuon SET NgayTraThucTe = ?, TienPhat = ?, DaDongPhat = ? "
            "WHERE MaPhieuMuon = ?",
            (ngay_iso, tien_phat, da_dong, ma_phieu),
        )
        # Hoàn kho có điều kiện: không bao giờ vượt SoLuongTong
        cur = conn.execute(
            "UPDATE Sach SET SoLuongCon = SoLuongCon + 1 "
            "WHERE MaSach = ? AND SoLuongCon < SoLuongTong",
            (ma_sach,),
        )
        if cur.rowcount == 0:
            # Kho đã đầy dù vẫn còn phiếu chưa trả -> dữ liệu Sach bị sửa tay sai.
            raise LoiNghiepVu(
                f"Dữ liệu kho của sách '{ten_sach}' không nhất quán "
                "(SoLuongCon đã bằng SoLuongTong). Đã hủy thao tác trả."
            )
        so_luong_con = conn.execute(
            "SELECT SoLuongCon FROM Sach WHERE MaSach = ?", (ma_sach,)
        ).fetchone()[0]

    return KetQuaTra(ma_phieu, ma_doc_gia, ma_sach, ten_sach, han_tra, ngay_iso,
                     so_ngay_tre, tien_phat, so_luong_con)


# ---------------------------------------------------------------------------
# Truy vấn hỗ trợ giao diện
# ---------------------------------------------------------------------------
def lay_phieu_dang_muon(ma_doc_gia=None, ngay_tham_chieu=None, db_path=DB_PATH):
    """
    Danh sách phiếu CHƯA trả (để người dùng chọn mã phiếu khi trả sách).

    Trả về list tuple:
        (MaPhieuMuon, MaDocGia, HoTen, MaSach, TenSach, NgayMuon, HanTra, SoNgayTre)
    SoNgayTre tính theo ngay_tham_chieu (mặc định hôm nay), 0 nếu chưa quá hạn.
    """
    ngay_iso = _chuan_hoa_ngay(ngay_tham_chieu, "Ngày tham chiếu").isoformat()
    sql = """
        SELECT p.MaPhieuMuon, p.MaDocGia, d.HoTen, p.MaSach, s.TenSach,
               p.NgayMuon, p.HanTra,
               MAX(0, CAST(julianday(?) - julianday(p.HanTra) AS INTEGER))
        FROM PhieuMuon p
        JOIN DocGia d ON d.MaDocGia = p.MaDocGia
        JOIN Sach   s ON s.MaSach   = p.MaSach
        WHERE p.NgayTraThucTe IS NULL
    """
    params = [ngay_iso]
    if ma_doc_gia is not None:
        sql += " AND p.MaDocGia = ?"
        params.append(_chuan_hoa_ma(ma_doc_gia, "Mã độc giả"))
    sql += " ORDER BY p.HanTra, p.MaPhieuMuon"
    with closing(get_connection(db_path)) as conn:
        return conn.execute(sql, params).fetchall()
