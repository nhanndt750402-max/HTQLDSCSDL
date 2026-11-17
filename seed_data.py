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

    book_ids = list(range(1, len(BOOKS) + 1))
    late_books = dict(zip(rng.sample(book_ids, len(late_readers)), late_readers))
    past_counts = rng.sample(book_ids, len(BOOKS))

    # 1. Tạo lịch sử trả đúng hạn trước, mỗi độc giả có lịch mượn riêng.
    next_borrow = {
        reader_id: today - timedelta(days=30 * (sum(past_counts) + 2))
        for reader_id in reader_ids
    }
    for book_id, count in zip(book_ids, past_counts):
        for _ in range(count - int(book_id in late_books)):
            reader_id = rng.choice(reader_ids)
            borrowed = next_borrow[reader_id]
            due = borrowed + timedelta(days=14)
            returned = borrowed + timedelta(days=rng.randint(2, 14))
            loans.append(
                (
                    reader_id,
                    book_id,
                    borrowed.isoformat(),
                    due.isoformat(),
                    returned.isoformat(),
                    0,
                    0,
                )
            )
            next_borrow[reader_id] = returned + timedelta(days=rng.randint(1, 4))

    # 2. Phiếu trả trễ là phiếu cuối trong lịch sử của các độc giả được chọn (tạo danh sách nợ phạt).
    for book_id, reader_id in late_books.items():
        borrowed = today - timedelta(days=rng.randint(45, 60))
        due = borrowed + timedelta(days=14)
        late_days = rng.randint(1, 12)
        returned = due + timedelta(days=late_days)
        loans.append(
            (
                reader_id,
                book_id,
                borrowed.isoformat(),
                due.isoformat(),
                returned.isoformat(),
                late_days * 5000,
                int(reader_id not in debtors),
            )
        )

    # 3. Khởi tạo số lượng tổng từng đầu sách (sách 1 luôn có tổng = 1 để giữ ca hết tồn kho).
    shuffled_books = rng.sample(BOOKS, len(BOOKS))
    book_totals = {
        book_id: (1 if book_id == 1 else rng.randint(3, 6))
        for book_id in book_ids
    }

    # 4. Sinh ngẫu nhiên 5 - 9 phiếu đang mượn cho nhóm độc giả đủ điều kiện (tối đa 3 cuốn/người).
    max_slots = len(eligible_readers) * 3
    num_active = rng.randint(5, min(9, max_slots))

    reader_active_books = {r_id: set() for r_id in eligible_readers}
    book_active_count = {b_id: 0 for b_id in book_ids}
    active_pairs = []

    # Đảm bảo sách số 1 luôn được mượn hết (SoLuongCon = 0) để kiểm thử quy tắc hết sách
    first_reader = rng.choice(eligible_readers)
    reader_active_books[first_reader].add(1)
    book_active_count[1] = 1
    active_pairs.append((first_reader, 1))

    while len(active_pairs) < num_active:
        avail_readers = [r for r in eligible_readers if len(reader_active_books[r]) < 3]
        if not avail_readers:
            break
        r_id = rng.choice(avail_readers)
        avail_books = [
            b
            for b in book_ids
            if b not in reader_active_books[r_id] and book_active_count[b] < book_totals[b]
        ]
        if not avail_books:
            break
        b_id = rng.choice(avail_books)
        reader_active_books[r_id].add(b_id)
        book_active_count[b_id] += 1
        active_pairs.append((r_id, b_id))

    # Chọn ngẫu nhiên 2 - 3 người trong số đang mượn bị trễ hạn với số ngày trễ khác nhau
    borrowers_with_active = list({r_id for r_id, _ in active_pairs})
    overdue_readers = set(
        rng.sample(borrowers_with_active, rng.randint(2, min(3, len(borrowers_with_active))))
    )
    overdue_assigned = set()

    for r_id, b_id in active_pairs:
        if r_id in overdue_readers and r_id not in overdue_assigned:
            # Mượn cách đây 16 - 28 ngày -> đã quá hạn 2 - 14 ngày
            borrowed = today - timedelta(days=rng.randint(16, 28))
            overdue_assigned.add(r_id)
        else:
            # Mượn cách đây 1 - 12 ngày -> vẫn trong hạn 14 ngày
            borrowed = today - timedelta(days=rng.randint(1, 12))

        due = borrowed + timedelta(days=14)
        loans.append(
            (r_id, b_id, borrowed.isoformat(), due.isoformat(), None, 0, 0)
        )

    for book_id, (title, author) in enumerate(shuffled_books, 1):
        total = book_totals[book_id]
        remaining = total - book_active_count[book_id]
        books.append((book_id, title, author, total, remaining))

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
