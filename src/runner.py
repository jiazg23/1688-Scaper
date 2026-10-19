"""Per-input limits, global product deduplication, and recoverable page snapshots."""

from contextlib import aclosing
from datetime import datetime, timezone

from .parser import CollectionError, AccessBlocked
from .pricing import quote


class RunFailed(CollectionError):
    pass


def input_specs(config):
    values = config.offer_ids if config.mode == "offer_ids" else config.terms
    return [{"index": i, "kind": config.mode, "value": value,
             "label": value}
            for i, value in enumerate(values, 1)]


class Runner:
    def __init__(self, config, collector, checkpoint):
        self.config, self.collector, self.checkpoint = config, collector, checkpoint
        self.products = {}
        self.summary = {"status": "running", "live_collection_validated": False, "inputs": [],
                        "product_count": 0, "notes": ["Development build: live 1688 collection has not been validated.",
                        "Displayed prices are not confirmed variant-specific bulk quotations."]}

    async def save(self):
        self.summary["product_count"] = len(self.products)
        self.summary["last_saved_at"] = datetime.now(timezone.utc).isoformat()
        await self.checkpoint(list(self.products.values()), self.summary)

    async def run(self):
        failure = None
        specs = input_specs(self.config)
        for spec in specs:
            outcome = {"index": spec["index"], "kind": spec["kind"], "label": spec["label"],
                       "status": "running", "pages": 0, "products": 0, "error": None}
            self.summary["inputs"].append(outcome)
            seen = set()  # Reset per keyword/offer, never consume later inputs' quota.
            try:
                async with aclosing(self.collector.pages(spec, self.config.max_pages)) as pages:
                    await self._consume(pages, spec, outcome, seen)
                if outcome["status"] == "running":
                    raise CollectionError("Search ended without a verified completion or configured limit.")
            except Exception as exc:
                outcome.update(status="partial" if seen else "failed", products=len(seen),
                               error=str(exc) if isinstance(exc, (CollectionError, ValueError)) else "Unexpected collector error; inspect the implementation.")
                for attribute in ("code", "stage", "diagnostic_key", "diagnostic_storage_failed"):
                    if hasattr(exc, attribute):
                        outcome["error_code" if attribute == "code" else attribute] = getattr(exc, attribute)
                # Access restrictions are terminal across the run. Never rotate
                # identity or move to later inputs after the site denies access.
                stop = isinstance(exc, AccessBlocked) or self.config.strict
                if stop:
                    failure = RunFailed(outcome["error"])
                    break
            finally:
                await self.save()
        processed = len(self.summary["inputs"])
        for spec in specs[processed:]:
            self.summary["inputs"].append({"index": spec["index"], "kind": spec["kind"], "label": spec["label"],
                                           "status": "not_started", "pages": 0, "products": 0,
                                           "error": "A terminal error stopped earlier collection."})
        errors = any(i["status"] in {"failed", "partial", "not_started"} for i in self.summary["inputs"])
        self.summary["status"] = "failed" if failure or not self.products else "partial" if errors else "complete"
        await self.save()
        if failure:
            raise failure
        if not self.products:
            raise RunFailed("No products collected. Check RUN_SUMMARY.json; blocked or unsupported pages are not successful empty searches.")
        return list(self.products.values())

    async def _consume(self, pages, spec, outcome, seen):
        async for batch in pages:
            outcome["pages"] += 1
            for product in batch["products"]:
                key = product["product_id"]
                if key in seen:
                    continue
                if len(seen) >= self.config.max_products:
                    break
                seen.add(key)
                source = {"index": spec["index"], "kind": spec["kind"], "label": spec["label"]}
                if key in self.products:
                    if source not in self.products[key]["matched_inputs"]:
                        self.products[key]["matched_inputs"].append(source)
                else:
                    self.products[key] = {**product, **quote(product, self.config.quantity),
                                          "matched_inputs": [source], "collected_at": datetime.now(timezone.utc).isoformat()}
            outcome["products"] = len(seen)
            if len(seen) >= self.config.max_products:
                outcome.update(status="limited", stop_reason="product_limit")
            elif batch["has_next"] is False:
                outcome.update(status="complete", stop_reason="last_page")
            elif outcome["pages"] >= self.config.max_pages:
                outcome.update(status="limited", stop_reason="page_limit")
            await self.save()
            if outcome["status"] in {"limited", "complete"}:
                break
