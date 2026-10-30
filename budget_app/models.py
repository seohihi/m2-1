from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal, List, Optional


@dataclass
class Transaction:
    id: str
    type: Literal["income", "expense"]
    date: str  # YYYY-MM-DD
    amount: int
    category: str
    memo: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            id=data["id"],
            type=data["type"],
            date=data["date"],
            amount=int(data["amount"]),
            category=data["category"],
            memo=data.get("memo", ""),
            tags=data.get("tags", []),
        )


@dataclass
class Budget:
    month: str  # YYYY-MM
    amount: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return cls(
            month=data["month"],
            amount=int(data["amount"]),
        )