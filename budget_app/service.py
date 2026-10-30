import csv
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from .models import Transaction
from .repository import FileRepository


class BudgetService:
    def __init__(self, repo: FileRepository):
        self.repo = repo

    def generate_next_id(self) -> str:
        max_num = 0
        for tx in self.repo.stream_transactions():
            if tx.id.startswith("TX-"):
                try:
                    num = int(tx.id.split("-")[1])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
        return f"TX-{max_num + 1:06d}"

    def add_transaction(self, tx_type: str, date_str: str, amount: int, category: str, memo: str, tags: List[str]) -> Transaction:
        # 입력 검증
        self._validate_date(date_str)
        if amount <= 0:
            raise ValueError("금액은 양수여야 합니다.")
        if tx_type not in ["income", "expense"]:
            raise ValueError("타입은 'income' 또는 'expense'여야 합니다.")
        
        valid_cats = self.repo.get_categories()
        if category not in valid_cats:
            raise ValueError(f"등록되지 않은 카테고리입니다: {category} (등록된 목록: {', '.join(valid_cats)})")

        tx_id = self.generate_next_id()
        tx = Transaction(
            id=tx_id,
            type=tx_type,  # type: ignore
            date=date_str,
            amount=amount,
            category=category,
            memo=memo,
            tags=tags
        )
        self.repo.append_transaction(tx)
        return tx

    def list_transactions(self, limit: int = 20) -> List[Transaction]:
        # 제너레이터 스트리밍 후 최신순(날짜 내림차순, ID 내림차순) 정렬
        all_txs = list(self.repo.stream_transactions())
        all_txs.sort(key=lambda x: (x.date, x.id), reverse=True)
        return all_txs[:limit]

    def search_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        tx_type: Optional[str] = None,
        query: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Transaction]:
        filtered = []
        for tx in self.repo.stream_transactions():
            if from_date and tx.date < from_date:
                continue
            if to_date and tx.date > to_date:
                continue
            if category and tx.category != category:
                continue
            if tx_type and tx.type != tx_type:
                continue
            if query and (query not in tx.memo):
                continue
            if tag and (tag not in tx.tags):
                continue
            filtered.append(tx)

        filtered.sort(key=lambda x: (x.date, x.id), reverse=True)
        return filtered

    def delete_transaction(self, tx_id: str) -> bool:
        all_txs = list(self.repo.stream_transactions())
        found = any(tx.id == tx_id for tx in all_txs)
        if not found:
            return False
        remaining = [tx for tx in all_txs if tx.id != tx_id]
        self.repo.rewrite_transactions(remaining)
        return True

    def update_transaction(
        self,
        tx_id: str,
        date_str: Optional[str] = None,
        tx_type: Optional[str] = None,
        category: Optional[str] = None,
        amount: Optional[int] = None,
        memo: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        all_txs = list(self.repo.stream_transactions())
        target_idx = -1
        for idx, tx in enumerate(all_txs):
            if tx.id == tx_id:
                target_idx = idx
                break
        if target_idx == -1:
            return False

        tx = all_txs[target_idx]
        if date_str:
            self._validate_date(date_str)
            tx.date = date_str
        if tx_type:
            if tx_type not in ["income", "expense"]:
                raise ValueError("타입은 'income' 또는 'expense'여야 합니다.")
            tx.type = tx_type  # type: ignore
        if category:
            valid_cats = self.repo.get_categories()
            if category not in valid_cats:
                raise ValueError(f"등록되지 않은 카테고리입니다: {category}")
            tx.category = category
        if amount is not None:
            if amount <= 0:
                raise ValueError("금액은 양수여야 합니다.")
            tx.amount = amount
        if memo is not None:
            tx.memo = memo
        if tags is not None:
            tx.tags = tags

        self.repo.rewrite_transactions(all_txs)
        return True

    def get_summary(self, month: str, top_n: int = 5) -> Tuple[int, int, int, List[Tuple[str, int]], Optional[int]]:
        total_income = 0
        total_expense = 0
        cat_expense: Dict[str, int] = {}
        has_data = False

        for tx in self.repo.stream_transactions():
            if tx.date.startswith(month):
                has_data = True
                if tx.type == "income":
                    total_income += tx.amount
                elif tx.type == "expense":
                    total_expense += tx.amount
                    cat_expense[tx.category] = cat_expense.get(tx.category, 0) + tx.amount

        if not has_data:
            raise ValueError(f"{month} 월의 데이터가 없습니다.")

        balance = total_income - total_expense
        sorted_cat = sorted(cat_expense.items(), key=lambda x: x[1], reverse=True)[:top_n]
        budget = self.repo.get_budgets().get(month)
        return total_income, total_expense, balance, sorted_cat, budget

    def add_category(self, name: str) -> bool:
        categories = self.repo.get_categories()
        if name in categories:
            raise ValueError(f"이미 존재하는 카테고리입니다: {name}")
        categories.append(name)
        self.repo.save_categories(categories)
        return True

    def remove_category(self, name: str) -> None:
        categories = self.repo.get_categories()
        if name not in categories:
            raise ValueError(f"존재하지 않는 카테고리입니다: {name}")

        # 사용 중인지 확인
        is_used = any(tx.category == name for tx in self.repo.stream_transactions())
        if is_used:
            raise ValueError(f"카테고리 '{name}'을(를) 사용 중인 거래 내역이 있어 삭제할 수 없습니다.")

        categories.remove(name)
        self.repo.save_categories(categories)

    def export_csv(self, file_path: str, month: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None) -> int:
        txs = self.search_transactions(from_date=from_date, to_date=to_date)
        if month:
            txs = [tx for tx in txs if tx.date.startswith(month)]

        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "type", "category", "amount", "memo", "tags"])
            for tx in txs:
                writer.writerow([tx.date, tx.type, tx.category, tx.amount, tx.memo, ",".join(tx.tags)])
        return len(txs)

    def import_csv(self, file_path: str) -> Tuple[int, int]:
        imported = 0
        skipped = 0
        valid_cats = set(self.repo.get_categories())

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    date = row["date"].strip()
                    tx_type = row["type"].strip()
                    category = row["category"].strip()
                    amount = int(row["amount"].strip())
                    memo = row.get("memo", "").strip()
                    tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]

                    self._validate_date(date)
                    if tx_type not in ["income", "expense"] or amount <= 0:
                        skipped += 1
                        continue

                    # 없는 카테고리는 자동 추가
                    if category not in valid_cats:
                        valid_cats.add(category)
                        self.repo.save_categories(list(valid_cats))

                    tx_id = self.generate_next_id()
                    tx = Transaction(id=tx_id, type=tx_type, date=date, amount=amount, category=category, memo=memo, tags=tags)  # type: ignore
                    self.repo.append_transaction(tx)
                    imported += 1
                except Exception:
                    skipped += 1
        return imported, skipped

    @staticmethod
    def _validate_date(date_str: str) -> None:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"날짜 형식이 올바르지 않습니다 (YYYY-MM-DD): {date_str}")