"""
main.py - TV5: Giao diện CLI cho Hệ thống quản lý mượn sách.

Chỉ lo phần hiển thị + nhập liệu, mọi nghiệp vụ gọi qua business_logic.py (TV3/TV4).
Nếu chưa có business_logic.py thật, tự động dùng business_logic_stub.py để test giao diện.
"""
import os

try:
    import business_logic as bl
except ImportError:
    import business_logic_stub as bl
    print("[!] Chưa có business_logic.py -> đang dùng dữ liệu giả (stub) để test giao diện.\n")

try:
    from tabulate import tabulate
except ImportError:  # fallback nếu chưa pip install tabulate
    def tabulate(rows, headers="keys", tablefmt="grid"):
        if not rows:
            return ""
        cols = list(rows[0].keys())
        w = {c: max(len(str(c)), *(len(str(r[c])) for r in rows)) for c in cols}
        line = "+" + "+".join("-" * (w[c] + 2) for c in cols) + "+"
        out = [line, "| " + " | ".join(str(c).ljust(w[c]) for c in cols) + " |", line]
        for r in rows:
            out.append("| " + " | ".join(str(r[c]).ljust(w[c]) for c in cols) + " |")
        out.append(line)
        return "\n".join(out)


# ---------- Tiện ích hiển thị ----------
def clear():
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    input("\nNhấn Enter để quay lại menu...")


def title(text):
    print("\n" + "=" * 60)
    print(text.center(60))
    print("=" * 60)


def show_table(rows, empty_msg="Không có dữ liệu."):
    """rows: list[dict]. In bảng đẹp bằng tabulate."""
    if not rows:
        print(empty_msg)
        return
    print(tabulate(rows, headers="keys", tablefmt="grid"))
    print(f"Tổng: {len(rows)} dòng")


def show_result(result):
    """Nghiệp vụ trả về (ok: bool, message: str)."""
    ok, msg = result
    print(("✅ " if ok else "❌ ") + str(msg))


def ask(prompt):
    return input(prompt).strip()


def ask_int(prompt, default=None):
    raw = ask(prompt)
    if not raw and default is not None:
        return default
    try:
        return int(raw)
    except ValueError:
        return None


# ---------- Các chức năng ----------
def ds_sach():
    title("DANH SÁCH SÁCH")
    show_table(bl.danh_sach_sach())


def ds_doc_gia():
    title("DANH SÁCH ĐỘC GIẢ")
    show_table(bl.danh_sach_doc_gia())


def muon_sach():
    title("MƯỢN SÁCH")
    ma_dg = ask("Mã độc giả (MSSV): ")
    ma_sach = ask("Mã sách: ")
    if not ma_dg or not ma_sach:
        print("❌ Không được để trống.")
        return
    try:
        show_result(bl.muon_sach(ma_dg, ma_sach))
    except Exception as e:
        print(f"❌ Lỗi hệ thống: {e}")


def tra_sach():
    title("TRẢ SÁCH")
    ma_phieu = ask_int("Mã phiếu mượn: ")
    if ma_phieu is None:
        print("❌ Mã phiếu phải là số.")
        return
    try:
        show_result(bl.tra_sach(ma_phieu))
    except Exception as e:
        print(f"❌ Lỗi hệ thống: {e}")


def phieu_tre_han():
    title("PHIẾU MƯỢN TRỄ HẠN")
    show_table(bl.danh_sach_phieu_tre(), "Không có phiếu trễ hạn 🎉")


def top_sach():
    title("TOP 5 SÁCH ĐƯỢC MƯỢN NHIỀU NHẤT")
    show_table(bl.top_sach_muon(5))


MENU = [
    ("1", "Xem danh sách sách", ds_sach),
    ("2", "Xem danh sách độc giả", ds_doc_gia),
    ("3", "Mượn sách", muon_sach),
    ("4", "Trả sách", tra_sach),
    ("5", "Báo cáo phiếu trễ hạn", phieu_tre_han),
    ("6", "Thống kê Top 5 sách mượn nhiều nhất", top_sach),
    ("0", "Thoát", None),
]


def main():
    while True:
        clear()
        title("QUẢN LÝ MƯỢN SÁCH")
        for key, label, _ in MENU:
            print(f"  [{key}] {label}")
        choice = ask("\nChọn chức năng: ")
        action = next((f for k, _, f in MENU if k == choice), "invalid")
        if choice == "0":
            print("Tạm biệt!")
            break
        if action == "invalid":
            print("❌ Lựa chọn không hợp lệ.")
        else:
            action()
        pause()


if __name__ == "__main__":
    main()