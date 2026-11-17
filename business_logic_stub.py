_sach = [
    {"MaSach": "S01", "TenSach": "Lập trình Python", "SoLuong": 3},
    {"MaSach": "S02", "TenSach": "Cấu trúc dữ liệu", "SoLuong": 0},
]
_dg = [{"MaDG": "2451010001", "HoTen": "Nguyễn Văn A"}]
_phieu = [{"MaPhieu": 1, "MaDG": "2451010001", "MaSach": "S01", "HanTra": "2026-11-01", "SoNgayTre": 15, "TienPhat": 75000}]


def danh_sach_sach(): return _sach
def danh_sach_doc_gia(): return _dg
def danh_sach_phieu_tre(): return _phieu
def top_sach_muon(n=5): return [{"Hạng": 1, "TenSach": "Lập trình Python", "SoLanMuon": 12}][:n]


def muon_sach(ma_dg, ma_sach):
    s = next((x for x in _sach if x["MaSach"] == ma_sach), None)
    if s is None: return False, "Không tìm thấy sách."
    if s["SoLuong"] <= 0: return False, "Sách đã hết."
    s["SoLuong"] -= 1
    return True, f"Mượn thành công sách {ma_sach}."


def tra_sach(ma_phieu):
    return (True, "Trả sách thành công.") if ma_phieu == 1 else (False, "Không tìm thấy phiếu.")