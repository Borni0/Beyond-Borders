"""Expense tracking service (spec §3.6 — Spending Tracker).

CRUD plus:

* ``import_csv`` — parse a CSV of expenses and bulk-create rows. Bad
  rows are skipped, not aborted, so a partial import always succeeds.
* ``export_csv`` — same shape as the import, in a stable order, so
  the round trip is symmetric.
* ``summarize`` — return a per-month + per-category rollup in the
  user's display currency (or the first currency they used if
  display currency isn't set in the request).

Money values are stored as ``Numeric(18, 4)`` strings. We do **not**
convert currencies here — the summary reports the totals per
currency the rows were logged in, and the user can filter.
"""

from __future__ import annotations

import csv
import io
import logging
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.repositories import expense_repo, study_plan_repo
from app.schemas.expense import (
    CategoryTotal,
    ExpenseCreate,
    ExpenseImportResult,
    ExpensePublic,
    ExpenseSummary,
    ExpenseUpdate,
    MonthlyBucket,
)

log = logging.getLogger(__name__)


# ---------- Validators -----------------------------------------------------


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _parse_amount(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    cleaned = raw.strip().replace(",", "").replace("$", "").replace("€", "").replace("£", "")
    if not cleaned:
        return None
    try:
        v = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    if v < 0:
        return None
    return v.quantize(Decimal("0.0001"))


def _parse_category(raw: str | None) -> str:
    raw = (raw or "").strip().lower()
    if not raw:
        return "miscellaneous"
    return raw[:32]


# ---------- Public projection --------------------------------------------


def _to_public(row) -> ExpensePublic:  # type: ignore[no-untyped-def]
    return ExpensePublic(
        id=row.id,
        user_id=row.user_id,
        category=row.category,
        description=row.description or "",
        amount=str(row.amount),
        currency=row.currency,
        spent_on=row.spent_on.isoformat() if row.spent_on else "",
        plan_id=row.plan_id,
        payment_method=row.payment_method,
        notes=row.notes,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


# ---------- CRUD ----------------------------------------------------------


def list_expenses(
    db: Session,
    user_id: str,
    *,
    plan_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
) -> list[ExpensePublic]:
    since_d = _parse_date(since) if since else None
    until_d = _parse_date(until) if until else None
    rows = expense_repo.list_expenses(
        db,
        user_id,
        plan_id=plan_id,
        since=since_d,
        until=until_d,
        limit=limit,
    )
    return [_to_public(r) for r in rows]


def create_expense(db: Session, user_id: str, body: ExpenseCreate) -> ExpensePublic:
    if body.plan_id is not None:
        plan = study_plan_repo.get_plan(db, user_id, body.plan_id)
        if plan is None:
            raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    spent_on = _parse_date(body.spent_on)
    if spent_on is None:
        raise ApiError(
            "VALIDATION_ERROR",
            "spent_on must be an ISO date (YYYY-MM-DD).",
            http_status=422,
        )
    amount = _parse_amount(str(body.amount))
    if amount is None:
        raise ApiError(
            "VALIDATION_ERROR",
            "amount must be a non-negative number.",
            http_status=422,
        )
    row = expense_repo.create_expense(
        db,
        user_id=user_id,
        plan_id=body.plan_id,
        category=_parse_category(body.category),
        description=(body.description or "").strip(),
        amount=amount,
        currency=body.currency.upper(),
        spent_on=spent_on,
        payment_method=(body.payment_method or None),
        notes=body.notes,
    )
    return _to_public(row)


def update_expense(
    db: Session, user_id: str, expense_id: str, body: ExpenseUpdate
) -> ExpensePublic:
    row = expense_repo.get_expense(db, user_id, expense_id)
    if row is None:
        raise ApiError("NOT_FOUND", "Expense not found.", http_status=404)
    payload = body.model_dump(mode="json", exclude_unset=True)
    if "plan_id" in payload and payload["plan_id"] is not None:
        plan = study_plan_repo.get_plan(db, user_id, payload["plan_id"])
        if plan is None:
            raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    if "spent_on" in payload and payload["spent_on"] is not None:
        new_date = _parse_date(payload["spent_on"])
        if new_date is None:
            raise ApiError(
                "VALIDATION_ERROR",
                "spent_on must be an ISO date (YYYY-MM-DD).",
                http_status=422,
            )
        payload["spent_on"] = new_date
    if "amount" in payload and payload["amount"] is not None:
        new_amount = _parse_amount(str(payload["amount"]))
        if new_amount is None:
            raise ApiError(
                "VALIDATION_ERROR",
                "amount must be a non-negative number.",
                http_status=422,
            )
        payload["amount"] = new_amount
    if "category" in payload and payload["category"] is not None:
        payload["category"] = _parse_category(payload["category"])
    if "currency" in payload and payload["currency"] is not None:
        payload["currency"] = payload["currency"].upper()
    row = expense_repo.update_expense(db, row, **payload)
    return _to_public(row)


def delete_expense(db: Session, user_id: str, expense_id: str) -> None:
    row = expense_repo.get_expense(db, user_id, expense_id)
    if row is None:
        raise ApiError("NOT_FOUND", "Expense not found.", http_status=404)
    expense_repo.delete_expense(db, row)


# ---------- CSV import / export -------------------------------------------


EXPECTED_HEADERS: tuple[str, ...] = (
    "category",
    "amount",
    "currency",
    "spent_on",
    "description",
    "plan_id",
    "payment_method",
    "notes",
)


def import_csv(db: Session, user_id: str, payload: str) -> ExpenseImportResult:
    """Parse ``payload`` (CSV text) and create expense rows.

    Headers must include ``category, amount, currency, spent_on`` —
    the other columns are optional. Bad rows are skipped and reported
    in ``errors``; valid rows are always created.
    """
    reader = csv.DictReader(io.StringIO(payload))
    if reader.fieldnames is None or not any(
        h in (reader.fieldnames or []) for h in ("category", "amount", "currency", "spent_on")
    ):
        raise ApiError(
            "VALIDATION_ERROR",
            "CSV is missing one of the required headers: "
            f"{', '.join(EXPECTED_HEADERS)}.",
            http_status=422,
        )
    created = 0
    skipped = 0
    errors: list[str] = []
    for idx, row in enumerate(reader, start=2):  # data rows start at line 2
        amount = _parse_amount(row.get("amount") or row.get("Amount"))
        spent_on = _parse_date(row.get("spent_on") or row.get("Spent on") or row.get("date"))
        currency = (row.get("currency") or row.get("Currency") or "").strip().upper()
        category = _parse_category(row.get("category") or row.get("Category"))
        if amount is None or spent_on is None or len(currency) != 3:
            skipped += 1
            errors.append(
                f"line {idx}: missing/invalid amount, date, or currency."
            )
            continue
        plan_id_raw = (row.get("plan_id") or "").strip() or None
        if plan_id_raw is not None:
            plan = study_plan_repo.get_plan(db, user_id, plan_id_raw)
            if plan is None:
                skipped += 1
                errors.append(
                    f"line {idx}: plan '{plan_id_raw}' not found or not yours."
                )
                continue
        try:
            expense_repo.create_expense(
                db,
                user_id=user_id,
                plan_id=plan_id_raw,
                category=category,
                description=(row.get("description") or "").strip(),
                amount=amount,
                currency=currency,
                spent_on=spent_on,
                payment_method=(row.get("payment_method") or "").strip() or None,
                notes=(row.get("notes") or "").strip() or None,
            )
            created += 1
        except Exception as exc:  # noqa: BLE001 — we report any row failure
            log.warning("expense import row %d failed: %s", idx, exc)
            skipped += 1
            errors.append(f"line {idx}: {exc}")
    return ExpenseImportResult(created=created, skipped=skipped, errors=errors)


def export_csv(
    db: Session,
    user_id: str,
    *,
    plan_id: str | None = None,
) -> str:
    rows = expense_repo.list_expenses(db, user_id, plan_id=plan_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPECTED_HEADERS)
    for row in rows:
        writer.writerow(
            [
                row.category,
                str(row.amount),
                row.currency,
                row.spent_on.isoformat() if row.spent_on else "",
                row.description or "",
                row.plan_id or "",
                row.payment_method or "",
                row.notes or "",
            ]
        )
    return buf.getvalue()


# ---------- Summary -------------------------------------------------------


def _bucket_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _zero() -> Decimal:
    return Decimal("0")


def summarize(
    db: Session,
    user_id: str,
    *,
    plan_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> ExpenseSummary:
    since_d = _parse_date(since) if since else None
    until_d = _parse_date(until) if until else None
    rows = list(
        expense_repo.list_expenses(
            db, user_id, plan_id=plan_id, since=since_d, until=until_d
        )
    )
    if not rows:
        return ExpenseSummary(
            base_currency="USD",
            total="0",
            count=0,
            months=[],
            by_category=[],
        )

    # Group per (currency, month, category).
    by_month: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(_zero)
    )
    counts_by_month: dict[tuple[str, str], int] = defaultdict(int)
    by_cat: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(_zero)
    )
    counts_by_cat: dict[tuple[str, str], int] = defaultdict(int)
    total_by_ccy: dict[str, Decimal] = defaultdict(_zero)
    count_total = 0
    for row in rows:
        ccy = row.currency.upper()
        month = _bucket_key(row.spent_on) if row.spent_on else "unknown"
        cat = row.category or "miscellaneous"
        amount = Decimal(str(row.amount))
        by_month[(ccy, month)][cat] += amount
        counts_by_month[(ccy, month)] += 1
        by_cat[(ccy, cat)][month] += amount
        counts_by_cat[(ccy, cat)] += 1
        total_by_ccy[ccy] += amount
        count_total += 1

    months_out: list[MonthlyBucket] = []
    for (ccy, month), cats in sorted(by_month.items(), key=lambda x: (x[0][1], x[0][0])):
        months_out.append(
            MonthlyBucket(
                month=month,
                currency=ccy,
                total=str(sum(cats.values(), Decimal("0")).quantize(Decimal("0.01"))),
                count=counts_by_month[(ccy, month)],
                by_category=[
                    CategoryTotal(
                        category=c,
                        total=str(t.quantize(Decimal("0.01"))),
                        currency=ccy,
                        count=0,
                    )
                    for c, t in sorted(
                        cats.items(), key=lambda x: x[1], reverse=True
                    )
                ],
            )
        )

    by_cat_out: list[CategoryTotal] = []
    for (ccy, cat), months in sorted(
        by_cat.items(), key=lambda x: (x[0][0], -sum(x[1].values(), Decimal("0")))
    ):
        by_cat_out.append(
            CategoryTotal(
                category=cat,
                currency=ccy,
                total=str(sum(months.values(), Decimal("0")).quantize(Decimal("0.01"))),
                count=counts_by_cat[(ccy, cat)],
            )
        )

    # Pick the largest-currency bucket as the "base" for the headline.
    base_ccy = max(total_by_ccy.items(), key=lambda kv: kv[1])[0]
    total = total_by_ccy[base_ccy].quantize(Decimal("0.01"))
    return ExpenseSummary(
        base_currency=base_ccy,
        total=str(total),
        count=count_total,
        months=months_out,
        by_category=by_cat_out,
    )


__all__ = [
    "EXPECTED_HEADERS",
    "create_expense",
    "delete_expense",
    "export_csv",
    "import_csv",
    "list_expenses",
    "summarize",
    "update_expense",
]