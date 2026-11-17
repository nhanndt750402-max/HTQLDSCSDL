"""
main_gui.py - TV5: Giao diện Tkinter cho Hệ thống quản lý thư viện.
Chạy: python main_gui.py
"""
import os
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from database import DB_PATH
import ui_adapter as bl


class TableTab(ttk.Frame):
    """Tab hiển thị bảng dữ liệu (Treeview) + nút Làm mới."""

    def __init__(self, parent, loader, top_bar_builder=None):
        super().__init__(parent)
        self.loader = loader

        top_bar = ttk.Frame(self)
        top_bar.pack(fill="x", padx=6, pady=6)

        if top_bar_builder:
            top_bar_builder(top_bar, self.refresh)

        ttk.Button(top_bar, text="🔄 Làm mới", command=self.refresh).pack(side="right")

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.tree = ttk.Treeview(frame, show="headings")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.status = ttk.Label(self, text="")
        self.status.pack(anchor="w", padx=6, pady=(0, 6))

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            rows = self.loader()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không tải được dữ liệu:\n{e}")
            return
        if not rows:
            self.tree["columns"] = ()
            self.status.config(text="Không có dữ liệu.")
            return
        cols = list(rows[0].keys())
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            width = 210 if c in ("TenSach", "TrangThai", "Email") else 110
            anchor = "w" if c in ("TenSach", "TacGia", "HoTen", "Email", "TrangThai") else "center"
            self.tree.column(c, anchor=anchor, width=width)
        for r in rows:
            self.tree.insert("", "end", values=[r[c] for c in cols])
        self.status.config(text=f"Tổng: {len(rows)} dòng")


class BorrowReturnTab(ttk.Frame):
    """Tab Mượn sách / Trả sách / Đóng tiền phạt."""

    def __init__(self, parent, on_done):
        super().__init__(parent)
        self.on_done = on_done

        # --- 1. Mượn sách ---
        muon = ttk.LabelFrame(self, text="1. Tạo phiếu mượn sách")
        muon.pack(fill="x", padx=12, pady=8)
        ttk.Label(muon, text="Mã độc giả (ID):").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.e_dg = ttk.Entry(muon, width=25)
        self.e_dg.grid(row=0, column=1, padx=6, pady=6)
        ttk.Label(muon, text="Mã sách (ID):").grid(row=1, column=0, padx=6, pady=6, sticky="e")
        self.e_sach = ttk.Entry(muon, width=25)
        self.e_sach.grid(row=1, column=1, padx=6, pady=6)
        ttk.Button(muon, text="📖 Mượn sách", command=self.muon).grid(row=0, column=2, rowspan=2, padx=12)

        # --- 2. Trả sách ---
        tra = ttk.LabelFrame(self, text="2. Trả sách (Xem Mã phiếu ở tab '📋 Đang mượn')")
        tra.pack(fill="x", padx=12, pady=8)
        ttk.Label(tra, text="Mã phiếu mượn:").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.e_phieu = ttk.Entry(tra, width=25)
        self.e_phieu.grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(tra, text="✅ Trả sách", command=self.tra).grid(row=0, column=2, padx=12)

        # --- 3. Đóng tiền phạt ---
        phat = ttk.LabelFrame(self, text="3. Thanh toán tiền phạt trễ hạn")
        phat.pack(fill="x", padx=12, pady=8)
        ttk.Label(phat, text="Mã độc giả (ID):").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.e_dg_phat = ttk.Entry(phat, width=25)
        self.e_dg_phat.grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(phat, text="💰 Đóng phạt", command=self.dong_phat).grid(row=0, column=2, padx=12)

    def _show(self, result):
        ok, msg = result
        (messagebox.showinfo if ok else messagebox.showerror)("Kết quả" if ok else "Thông báo", msg)
        if ok:
            self.on_done()

    def muon(self):
        ma_dg, ma_sach = self.e_dg.get().strip(), self.e_sach.get().strip()
        if not ma_dg or not ma_sach:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đủ Mã độc giả và Mã sách.")
            return
        self._show(bl.muon_sach(ma_dg, ma_sach))

    def tra(self):
        raw = self.e_phieu.get().strip()
        if not raw:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Mã phiếu mượn.")
            return
        self._show(bl.tra_sach(raw))

    def dong_phat(self):
        raw = self.e_dg_phat.get().strip()
        if not raw:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Mã độc giả cần đóng phạt.")
            return
        self._show(bl.dong_tien_phat(raw))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hệ thống Quản lý Thư viện (SQLite)")
        self.geometry("920x560")

        self._khoi_dong_db()

        # Thanh tiêu đề & nút đổi MSSV
        header = ttk.Frame(self)
        header.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(
            header,
            text="HỆ THỐNG QUẢN LÝ MƯỢN TRẢ SÁCH",
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")
        ttk.Button(
            header,
            text="🔁 Tạo lại dữ liệu theo MSSV khác",
            command=self.reset_mssv,
        ).pack(side="right")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tables = [
            TableTab(self.nb, bl.danh_sach_sach, self._build_add_sach_bar),
            TableTab(self.nb, bl.danh_sach_doc_gia, self._build_add_dg_bar),
            TableTab(self.nb, bl.danh_sach_phieu_dang_muon),
            TableTab(self.nb, bl.danh_sach_phieu_tre),
            TableTab(self.nb, lambda: bl.top_sach_muon(5)),
        ]
        self.nb.add(self.tables[0], text="📚 Sách")
        self.nb.add(self.tables[1], text="👤 Độc giả")
        self.nb.add(BorrowReturnTab(self.nb, self.refresh_all), text="📖 Mượn / Trả / Đóng phạt")
        self.nb.add(self.tables[2], text="📋 Đang mượn")
        self.nb.add(self.tables[3], text="⏰ Trễ hạn")
        self.nb.add(self.tables[4], text="🏆 Top 5 sách")

        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.refresh_all()

    def _khoi_dong_db(self):
        if not os.path.exists(DB_PATH):
            mssv = simpledialog.askstring(
                "Khởi tạo dữ liệu",
                "Chưa có CSDL thuvien.db.\nNhập MSSV để tạo dữ liệu mẫu:",
                parent=self,
            )
            bl.khoi_tao_du_lieu(mssv or "056207003633", tao_lai=False)
        else:
            bl.khoi_tao_du_lieu(tao_lai=False)

    def reset_mssv(self):
        mssv = simpledialog.askstring(
            "Tạo lại dữ liệu mẫu",
            "Nhập MSSV mới (sẽ ghi đè thuvien.db hiện tại):",
            parent=self,
        )
        if mssv and mssv.strip():
            bl.khoi_tao_du_lieu(mssv.strip(), tao_lai=True)
            self.refresh_all()
            messagebox.showinfo("Hoàn tất", f"Đã khởi tạo lại CSDL theo MSSV: {mssv.strip()}")

    def _build_add_sach_bar(self, parent, refresh_cb):
        ttk.Label(parent, text="Tên sách:").pack(side="left", padx=(0, 4))
        e_ten = ttk.Entry(parent, width=22)
        e_ten.pack(side="left", padx=(0, 8))
        ttk.Label(parent, text="Tác giả:").pack(side="left", padx=(0, 4))
        e_tg = ttk.Entry(parent, width=18)
        e_tg.pack(side="left", padx=(0, 8))
        ttk.Label(parent, text="SL:").pack(side="left", padx=(0, 4))
        e_sl = ttk.Entry(parent, width=5)
        e_sl.pack(side="left", padx=(0, 8))

        def submit():
            ok, msg = bl.them_sach(e_ten.get(), e_tg.get(), e_sl.get())
            (messagebox.showinfo if ok else messagebox.showerror)("Thông báo", msg)
            if ok:
                e_ten.delete(0, "end")
                e_tg.delete(0, "end")
                e_sl.delete(0, "end")
                refresh_cb()

        ttk.Button(parent, text="➕ Thêm sách", command=submit).pack(side="left")

    def _build_add_dg_bar(self, parent, refresh_cb):
        ttk.Label(parent, text="Họ tên:").pack(side="left", padx=(0, 4))
        e_ten = ttk.Entry(parent, width=22)
        e_ten.pack(side="left", padx=(0, 8))
        ttk.Label(parent, text="Email:").pack(side="left", padx=(0, 4))
        e_email = ttk.Entry(parent, width=24)
        e_email.pack(side="left", padx=(0, 8))

        def submit():
            ok, msg = bl.them_doc_gia(e_ten.get(), e_email.get())
            (messagebox.showinfo if ok else messagebox.showerror)("Thông báo", msg)
            if ok:
                e_ten.delete(0, "end")
                e_email.delete(0, "end")
                refresh_cb()

        ttk.Button(parent, text="➕ Thêm độc giả", command=submit).pack(side="left")

    def on_tab_change(self, _event):
        tab = self.nametowidget(self.nb.select())
        if isinstance(tab, TableTab):
            tab.refresh()

    def refresh_all(self):
        for t in self.tables:
            t.refresh()


if __name__ == "__main__":
    App().mainloop()
