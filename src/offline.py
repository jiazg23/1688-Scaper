"""Parse a saved page without executing its scripts or making network requests."""

import argparse
import json
import sys
from pathlib import Path

from .exports import csv_text, supplier_rows, SUPPLIER_FIELDS
from .parser import parse_search
from .pricing import quote


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("--header", type=Path, help="Optional saved currency header/dropdown HTML.")
    parser.add_argument("--quantity", type=int, default=100)
    parser.add_argument("--format", choices=["json", "csv", "suppliers"], default="json")
    args = parser.parse_args()
    if args.quantity < 1:
        parser.error("quantity must be a positive integer")
    html = args.html.read_text(encoding="utf-8")
    if args.header:
        html = args.header.read_text(encoding="utf-8") + html
    products = parse_search(html)["products"]
    products = [{**p, **quote(p, args.quantity), "matched_inputs": [{"kind": "saved_html", "label": args.html.name}]} for p in products]
    if args.format == "json":
        print(json.dumps(products, ensure_ascii=False, indent=2))
    elif args.format == "csv":
        sys.stdout.write(csv_text(products))
    else:
        sys.stdout.write(csv_text(supplier_rows(products), SUPPLIER_FIELDS))


if __name__ == "__main__":
    main()
