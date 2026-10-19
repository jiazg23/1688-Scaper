"""Deterministic exports; no extra dataset rows or charges for supplier summaries."""

import csv
import io
import json

FIELDS = ["product_id", "title", "product_url", "image_url", "display_price", "currency",
          "price_symbol", "currency_source", "moq", "moq_text", "quantity_unit", "price_basis",
          "price_tiers", "order_quantity", "quote_status", "applicable_unit_price", "product_subtotal",
          "subtotal_excludes", "supplier_id", "supplier_name", "supplier_url", "supplier_years",
          "supplier_rating", "sales_text", "marketing_tags", "is_sponsored", "verified_supplier",
          "manufacturer", "matched_inputs", "extraction_source", "collected_at",
          "variants", "product_attributes", "image_urls", "product_rating", "moq_scope",
          "supplier_tenure_text", "detail_completeness", "login_required_for_full_details"]
SUPPLIER_FIELDS = ["supplier_id", "supplier_name", "supplier_url", "product_count", "product_ids", "currencies", "matched_inputs"]


def cell(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    value = str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")):
        value = "'" + value
    return value


def csv_text(rows, fields=FIELDS):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: cell(row.get(key)) for key in fields})
    return "\ufeff" + stream.getvalue()


def supplier_rows(products):
    suppliers = {}
    for p in products:
        key = p.get("supplier_url") or p.get("supplier_id")
        if not key:
            continue  # Names alone are not safe company identifiers.
        row = suppliers.setdefault(key, {"supplier_id": p.get("supplier_id"),
                                         "supplier_name": p.get("supplier_name"), "supplier_url": p.get("supplier_url"),
                                         "product_count": 0, "product_ids": [], "currencies": [], "matched_inputs": []})
        row["product_ids"].append(p["product_id"])
        row["product_count"] += 1
        if p.get("currency") and p["currency"] not in row["currencies"]:
            row["currencies"].append(p["currency"])
        for source in p.get("matched_inputs", []):
            if source not in row["matched_inputs"]:
                row["matched_inputs"].append(source)
    return list(suppliers.values())
