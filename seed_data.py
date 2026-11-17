"""Tạo dữ liệu mẫu theo MSSV vào CSDL trống."""

import argparse
import random
from contextlib import closing
from datetime import date, timedelta

from database import DB_PATH, get_connection, init_db

READERS = ("Nguyễn An", "Trần Bình", "Lê Chi", "Phạm Dũng", "Võ Hà", "Đỗ Hạnh")
BOOKS = (
    ("Dế Mèn phiêu lưu ký", "Tô Hoài"),
    ("Đất rừng phương Nam", "Đoàn Giỏi"),
    ("Quê nội", "Võ Quảng"),
    ("Lá cờ thêu sáu chữ vàng", "Nguyễn Huy Tưởng"),
    ("Tôi thấy hoa vàng trên cỏ xanh", "Nguyễn Nhật Ánh"),
    ("Vừa nhắm mắt vừa mở cửa sổ", "Nguyễn Ngọc Thuần"),
)


def seed_database(mssv, db_path=DB_PATH, as_of=None):
    if not mssv.strip():
        raise ValueError("MSSV không được để trống.")

    rng = random.Random(mssv.strip())
    today = as_of or date.today()
    readers = [
        (reader_id, name, f"docgia{reader_id}@example.test")
        for reader_id, name in enumerate(rng.sample(READERS, len(READERS)), 1)
    ]
    books = []
    loans = []
    reader_ids = [reader_id for reader_id, _, _ in readers]
    late_readers = rng.sample(reader_ids, rng.randint(3, 4))
    debtors = set(rng.sample(late_readers, rng.randint(2, len(late_readers) - 1)))
    eligible_readers = [reader_id for reader_id in reader_ids if reader_id not in debtors]

    book_ids = range(1, len(BOOKS) + 1)
    late_books = dict(zip(rng.sample(book_ids, len(late_readers)), late_readers))
    past_counts = rng.sample(book_ids, len(BOOKS))
    active_books = [1, *rng.sample(range(2, len(BOOKS) + 1), len(eligible_readers) - 1)]
    active_readers = dict(zip(active_books, rng.sample(eligible_readers, len(eligible_readers))))

    # Tạo lịch sử trả đúng hạn trước, mỗi độc giả có lịch mượn riêng.
    next_borrow = {reader_id: today - timedelta(days=30 * (sum(past_counts) + 2))
                   for reader_id in reader_ids}
    for book_id, count in zip(book_ids, past_counts):
        for _ in range(count - int(book_id in late_books)):
            reader_id = rng.choice(reader_ids)
            borrowed = next_borrow[reader_id]
            due = borrowed + timedelta(days=14)
            returned = borrowed + timedelta(days=rng.randint(2, 14))
            loans.append(
                (reader_id, book_id, borrowed.isoformat(), due.isoformat(),
                 returned.isoformat(), 0, 0)
            )
            next_borrow[reader_id] = returned + timedelta(days=rng.randint(1, 4))

    # Phiếu trả trễ là phiếu cuối trong lịch sử của các độc giả được chọn.
    for book_id, reader_id in late_books.items():
        borrowed = today - timedelta(days=rng.randint(45, 60))
        due = borrowed + timedelta(days=14)
        late_days = rng.randint(1, 12)
        returned = due + timedelta(days=late_days)
        loans.append(
            (reader_id, book_id, borrowed.isoformat(), due.isoformat(),
             returned.isoformat(), late_days * 5000, int(reader_id not in debtors))
        )

    # Giữ một ca sách hết tồn và quá hạn để kiểm thử.
    for book_id, (title, author) in enumerate(rng.sample(BOOKS, len(BOOKS)), 1):
        total = 1 if book_id == 1 else rng.randint(2, 6)
        books.append((book_id, title, author, total, total - int(book_id in active_readers)))
        if book_id in active_readers:
            borrowed = today - timedelta(days=21 if book_id == 1 else rng.randint(1, 10))
            due = borrowed + timedelta(days=14)
            loans.append(
                (active_readers[book_id], book_id, borrowed.isoformat(), due.isoformat(),
                 None, 0, 0)
            )

    init_db(db_path)
    with closing(get_connection(db_path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        occupied = conn.execute(
            "SELECT EXISTS (SELECT 1 FROM DocGia) OR EXISTS (SELECT 1 FROM Sach) "
            "OR EXISTS (SELECT 1 FROM PhieuMuon)"
        ).fetchone()[0]
        if occupied:
            raise ValueError("CSDL đã có dữ liệu. Hãy chọn file mẫu mới bằng --db.")
        conn.executemany(
            "INSERT INTO DocGia (MaDocGia, HoTen, Email) VALUES (?, ?, ?)", readers
        )
        conn.executemany(
            "INSERT INTO Sach (MaSach, TenSach, TacGia, SoLuongTong, SoLuongCon) "
            "VALUES (?, ?, ?, ?, ?)",
            books,
        )
        conn.executemany(
            "INSERT INTO PhieuMuon (MaDocGia, MaSach, NgayMuon, HanTra, NgayTraThucTe, "
            "TienPhat, DaDongPhat) VALUES (?, ?, ?, ?, ?, ?, ?)",
            loans,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tạo dữ liệu SQLite mẫu theo MSSV.")
    parser.add_argument("mssv")
    parser.add_argument("--db", default=DB_PATH, help="Đường dẫn file SQLite")
    parser.add_argument("--as-of", type=date.fromisoformat, help="Ngày tham chiếu YYYY-MM-DD")
    args = parser.parse_args()
    try:
        seed_database(args.mssv, args.db, args.as_of)
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")
    print(f"Đã tạo dữ liệu mẫu: {args.db}")
