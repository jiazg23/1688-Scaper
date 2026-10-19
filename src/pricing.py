"""Money is decimal. A search-card teaser price is never a firm tier quote."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def decimal_text(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            return None
        return format(result, "f")
    except (InvalidOperation, TypeError, ValueError):
        return None


def quote(product: dict, quantity: int) -> dict:
    result = {"order_quantity": quantity, "quote_status": "listing_price_only",
              "applicable_unit_price": None, "product_subtotal": None,
              "subtotal_excludes": ["shipping", "tax", "duties", "service_fees"]}
    moq = product.get("moq")
    if moq is not None and quantity < moq:
        result["quote_status"] = "below_moq"
        return result
    if product.get("price_basis") in {"variants", "starting_price_with_variants"}:
        result["quote_status"] = "variant_selection_required"
        return result
    tiers = product.get("price_tiers") or []
    if not tiers:
        return result
    if not product.get("currency"):
        result["quote_status"] = "currency_unknown"
        return result
    if product.get("price_basis") != "quantity_tiers":
        result["quote_status"] = "variant_selection_required"
        return result
    if moq is None or product.get("quantity_unit") not in {"piece", "unit", "pcs", "件", "个"}:
        result["quote_status"] = "quantity_basis_unknown"
        return result
    ordered = sorted(tiers, key=lambda t: t.get("min_quantity", 0))
    previous_min = previous_max = None
    for index, tier in enumerate(ordered):
        low, high = tier.get("min_quantity"), tier.get("max_quantity")
        amount = decimal_text(tier.get("unit_price"))
        invalid = (type(low) is not int or low < 1 or amount is None
                   or (high is not None and (type(high) is not int or high < low))
                   or (previous_min is not None and low <= previous_min)
                   or (previous_max is not None and low <= previous_max)
                   or (index < len(ordered) - 1 and high is None))
        if invalid:
            result["quote_status"] = "invalid_tiers"
            return result
        previous_min, previous_max = low, high
    eligible = [t for t in ordered if t["min_quantity"] <= quantity and
                (t.get("max_quantity") is None or quantity <= t["max_quantity"])]
    if not eligible:
        result["quote_status"] = "quantity_not_covered"
        return result
    price = Decimal(str(eligible[-1]["unit_price"]))
    result.update(quote_status="published_tier_subtotal", applicable_unit_price=format(price, "f"),
                  product_subtotal=format((price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f"))
    return result
