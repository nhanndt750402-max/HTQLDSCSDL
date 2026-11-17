"""
main_gui.py - TV5: Giao diện Tkinter cho Hệ thống quản lý mượn sách.
Chạy:  python main_gui.py
Dùng chung các hàm trong business_logic.py với bản CLI (main.py).
"""
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import business_logic as bl
except ImportError:
    import business_logic_stub as bl  # dữ liệu giả để test giao diện


class TableTab(ttk.Frame):
    """Một tab hiển thị bảng dữ liệu (Treeview) + nút Làm mới."""

    def __init__(self, parent, loader):
        super().__init__(parent)
        self.loader = loader

        ttk.Button(self, text="🔄 Làm mới", command=self.refresh).pack(anchor="e", padx=6, pady=6)

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
            self.tree.column(c, anchor="center", width=120)
        for r in rows:
            self.tree.insert("", "end", values=[r[c] for c in cols])
        self.status.config(text=f"Tổng: {len(rows)} dòng")


class BorrowReturnTab(ttk.Frame):
    """Tab Mượn / Trả sách (form nhập liệu)."""

    def __init__(self, parent, on_done):
        super().__init__(parent)
        self.on_done = on_done  # gọi lại để làm mới các bảng sau khi mượn/trả

        # --- Mượn sách ---
        muon = ttk.LabelFrame(self, text="Mượn sách")
        muon.pack(fill="x", padx=12, pady=12)
        ttk.Label(muon, text="Mã độc giả (MSSV):").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.e_dg = ttk.Entry(muon, width=25)
        self.e_dg.grid(row=0, column=1, padx=6, pady=6)
        ttk.Label(muon, text="Mã sách:").grid(row=1, column=0, padx=6, pady=6, sticky="e")
        self.e_sach = ttk.Entry(muon, width=25)
        self.e_sach.grid(row=1, column=1, padx=6, pady=6)
        ttk.Button(muon, text="Mượn", command=self.muon).grid(row=2, column=1, pady=8, sticky="w")

        # --- Trả sách ---
        tra = ttk.LabelFrame(self, text="Trả sách")
        tra.pack(fill="x", padx=12, pady=12)
        ttk.Label(tra, text="Mã phiếu mượn:").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.e_phieu = ttk.Entry(tra, width=25)
        self.e_phieu.grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(tra, text="Trả", command=self.tra).grid(row=1, column=1, pady=8, sticky="w")

    def _show(self, result):
        ok, msg = result
        (messagebox.showinfo if ok else messagebox.showerror)("Kết quả" if ok else "Lỗi", msg)
        if ok:
            self.on_done()

    def muon(self):
        ma_dg, ma_sach = self.e_dg.get().strip(), self.e_sach.get().strip()
        if not ma_dg or not ma_sach:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đủ mã độc giả và mã sách.")
            return
        try:
            self._show(bl.muon_sach(ma_dg, ma_sach))
        except Exception as e:
            messagebox.showerror("Lỗi hệ thống", str(e))

    def tra(self):
        raw = self.e_phieu.get().strip()
        if not raw.isdigit():
            messagebox.showwarning("Sai dữ liệu", "Mã phiếu phải là số.")
            return
        try:
            self._show(bl.tra_sach(int(raw)))
        except Exception as e:
            messagebox.showerror("Lỗi hệ thống", str(e))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quản lý mượn sách")
        self.geometry("860x520")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tables = [
            TableTab(self.nb, bl.danh_sach_sach),
            TableTab(self.nb, bl.danh_sach_doc_gia),
            TableTab(self.nb, bl.danh_sach_phieu_tre),
            TableTab(self.nb, lambda: bl.top_sach_muon(5)),
        ]
        self.nb.add(self.tables[0], text="📚 Sách")
        self.nb.add(self.tables[1], text="👤 Độc giả")
        self.nb.add(BorrowReturnTab(self.nb, self.refresh_all), text="📖 Mượn / Trả")
        self.nb.add(self.tables[2], text="⏰ Trễ hạn")
        self.nb.add(self.tables[3], text="🏆 Top 5 sách")

        # Mỗi lần chuyển tab thì tự tải lại dữ liệu
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.refresh_all()

    def on_tab_change(self, _event):
        tab = self.nametowidget(self.nb.select())
        if isinstance(tab, TableTab):
            tab.refresh()

    def refresh_all(self):
        for t in self.tables:
            t.refresh()


if __name__ == "__main__":
    App().mainloop()