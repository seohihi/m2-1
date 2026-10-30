import os
import json
import tempfile
from typing import Generator, List, Set
from .models import Transaction, Budget


class FileRepository:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.tx_file = os.path.join(data_dir, "transactions.jsonl")
        self.cat_file = os.path.join(data_dir, "categories.jsonl")
        self.budget_file = os.path.join(data_dir, "budgets.jsonl")
        self._ensure_files()

    def _ensure_files(self) -> None:
        """저장 폴더 및 3개 영구 저장 파일 초기화"""
        os.makedirs(self.data_dir, exist_ok=True)
        for filepath in [self.tx_file, self.cat_file, self.budget_file]:
            if not os.path.exists(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    pass

        # 카테고리가 비어있으면 기본 카테고리 자동 생성 (안 A)
        if os.path.getsize(self.cat_file) == 0:
            default_categories = ["food", "transport", "rent", "salary", "shopping", "etc"]
            with open(self.cat_file, "w", encoding="utf-8") as f:
                for cat in default_categories:
                    f.write(json.dumps({"name": cat}, ensure_ascii=False) + "\n")

    # 제너레이터 기반 거래 내역 스트리밍
    def stream_transactions(self) -> Generator[Transaction, None, None]:
        if not os.path.exists(self.tx_file):
            return
        with open(self.tx_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield Transaction.from_dict(json.loads(line))

    def append_transaction(self, tx: Transaction) -> None:
        with open(self.tx_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")

    # 원자적 파일 교체 (임시 파일 작성 -> rename)
    def rewrite_transactions(self, transactions: List[Transaction]) -> None:
        dir_name = os.path.dirname(self.tx_file)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tf:
            temp_path = tf.name
            for tx in transactions:
                tf.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")
        os.replace(temp_path, self.tx_file)

    # 카테고리 읽기 및 저장
    def get_categories(self) -> List[str]:
        categories = []
        if os.path.exists(self.cat_file):
            with open(self.cat_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        categories.append(json.loads(line)["name"])
        return categories

    def save_categories(self, categories: List[str]) -> None:
        dir_name = os.path.dirname(self.cat_file)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tf:
            temp_path = tf.name
            for cat in categories:
                tf.write(json.dumps({"name": cat}, ensure_ascii=False) + "\n")
        os.replace(temp_path, self.cat_file)

    # 예산 읽기 및 저장
    def get_budgets(self) -> dict[str, int]:
        budgets = {}
        if os.path.exists(self.budget_file):
            with open(self.budget_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        budgets[data["month"]] = int(data["amount"])
        return budgets

    def set_budget(self, month: str, amount: int) -> None:
        budgets = self.get_budgets()
        budgets[month] = amount
        dir_name = os.path.dirname(self.budget_file)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tf:
            temp_path = tf.name
            for m, amt in budgets.items():
                tf.write(json.dumps({"month": m, "amount": amt}, ensure_ascii=False) + "\n")
        os.replace(temp_path, self.budget_file)