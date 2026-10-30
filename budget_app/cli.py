import argparse
from typing import List
from .service import BudgetService
from .decorators import handle_cli_errors


def print_table(rows: List[List[str]], headers: List[str]) -> None:
    """보너스: 외부 라이브러리 없이 터미널 가독성을 높이는 정렬 포매터"""
    if not rows:
        print("내역이 없습니다.")
        return
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))

    header_fmt = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    sep = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_fmt)
    print(sep)
    for row in rows:
        print(" | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row)))


class CLIController:
    def __init__(self, service: BudgetService):
        self.service = service

    @handle_cli_errors
    def handle_add(self, args) -> None:
        print("--- [대화형 거래 추가] ---")
        date_str = input("날짜(YYYY-MM-DD): ").strip()
        tx_type = input("타입(income/expense): ").strip()
        category = input("카테고리: ").strip()
        amount_input = input("금액(양수): ").strip()
        if not amount_input.isdigit():
            raise ValueError("금액은 숫자만 입력 가능합니다.")
        amount = int(amount_input)
        memo = input("메모(선택): ").strip()
        tags_input = input("태그(쉼표로 구분, 없으면 엔터): ").strip()
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]

        tx = self.service.add_transaction(tx_type, date_str, amount, category, memo, tags)
        print(f"[저장 완료] id={tx.id}")

    @handle_cli_errors
    def handle_list(self, args) -> None:
        txs = self.service.list_transactions(limit=args.limit)
        headers = ["ID", "Date", "Type", "Category", "Amount", "Memo", "Tags"]
        rows = [[t.id, t.date, t.type, t.category, f"{t.amount:,}원", t.memo, ",".join(t.tags)] for t in txs]
        print_table(rows, headers)

    @handle_cli_errors
    def handle_search(self, args) -> None:
        txs = self.service.search_transactions(
            from_date=args.from_date,
            to_date=args.to_date,
            category=args.category,
            tx_type=args.type,
            query=args.q,
            tag=args.tag
        )
        headers = ["ID", "Date", "Type", "Category", "Amount", "Memo", "Tags"]
        rows = [[t.id, t.date, t.type, t.category, f"{t.amount:,}원", t.memo, ",".join(t.tags)] for t in txs]
        print_table(rows, headers)

    @handle_cli_errors
    def handle_delete(self, args) -> None:
        success = self.service.delete_transaction(args.id)
        if success:
            print(f"[삭제 성공] id={args.id}")
        else:
            raise ValueError(f"존재하지 않는 거래 ID입니다: {args.id}")

    @handle_cli_errors
    def handle_update(self, args) -> None:
        print(f"--- [거래 수정: id={args.id}] (변경하지 않을 항목은 엔터) ---")
        date_str = input("새 날짜(YYYY-MM-DD): ").strip() or None
        tx_type = input("새 타입(income/expense): ").strip() or None
        category = input("새 카테고리: ").strip() or None
        amount_input = input("새 금액: ").strip()
        amount = int(amount_input) if amount_input else None
        memo = input("새 메모: ").strip()
        memo = memo if memo != "" else None
        tags_input = input("새 태그(쉼표 구분): ").strip()
        tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else None

        success = self.service.update_transaction(args.id, date_str, tx_type, category, amount, memo, tags)
        if success:
            print(f"[수정 완료] id={args.id}")
        else:
            raise ValueError(f"존재하지 않는 거래 ID입니다: {args.id}")

    @handle_cli_errors
    def handle_summary(self, args) -> None:
        income, expense, balance, top_cats, budget = self.service.get_summary(args.month, top_n=args.top)
        print(f"총 수입: {income:,}원")
        print(f"총 지출: {expense:,}원")
        print(f"잔액: {balance:,}원")
        if budget is not None:
            usage = (expense / budget) * 100 if budget > 0 else 0
            warn = " [경고: 예산 초과!]" if expense > budget else ""
            print(f"예산: {budget:,}원 (사용률 {usage:.1f}%){warn}")
        print(f"\n지출 TOP {args.top}")
        for idx, (cat, amt) in enumerate(top_cats, 1):
            print(f"{idx}) {cat} {amt:,}원")

    @handle_cli_errors
    def handle_budget(self, args) -> None:
        if args.budget_action == "set":
            self.service.repo.set_budget(args.month, args.amount)
            print(f"[저장 완료] {args.month} 예산 {args.amount:,}원")

    @handle_cli_errors
    def handle_category(self, args) -> None:
        if args.cat_action == "list":
            cats = self.service.repo.get_categories()
            for cat in cats:
                print(f"- {cat}")
        elif args.cat_action == "add":
            name = input("카테고리명: ").strip()
            self.service.add_category(name)
            print(f"[저장 완료] category={name}")
        elif args.cat_action == "remove":
            self.service.remove_category(args.name)
            print(f"[삭제 완료] category={args.name}")

    @handle_cli_errors
    def handle_export(self, args) -> None:
        if not args.month and not (args.from_date and args.to_date):
            raise ValueError("--month 또는 (--from-date 및 --to-date) 조건이 필요합니다.")
        count = self.service.export_csv(args.out, month=args.month, from_date=args.from_date, to_date=args.to_date)
        print(f"[완료] {args.out} ({count} records)")

    @handle_cli_errors
    def handle_import(self, args) -> None:
        imported, skipped = self.service.import_csv(args.from_file)
        print(f"[완료] imported={imported} skipped={skipped}")