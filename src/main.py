"""Apify entrypoint. Import/startup checks never contact the target website."""

import asyncio
import os
import sys
from contextlib import asynccontextmanager

from apify import Actor
from playwright.async_api import async_playwright

from . import __version__
from .collector import BrowserCollector
from .config import Config
from .exports import csv_text, supplier_rows, SUPPLIER_FIELDS
from .runner import Runner
from .proxy import browser_proxy
from .elim import data_source, ElimSettings, ElimCollector, ProviderError


@asynccontextmanager
async def collection_backend(config, on_failure, log, environ=None):
    environ = os.environ if environ is None else environ
    if data_source(environ) == "elim":
        settings = ElimSettings.from_env(environ)
        charging = Actor.get_charging_manager()
        pricing = charging.get_pricing_info()
        allowance = None
        if pricing.is_pay_per_event:
            event = "apify-default-dataset-item"
            if pricing.per_event_prices.get(event, 0) <= 0:
                raise ProviderError("Configure a positive per-product dataset event price before using Elim with PPE. No provider call was made.", "provider_billing_setup")
            allowance = charging.calculate_max_event_charge_count_within_limit(event)
        log("Elim API backend selected explicitly. No browser, 1688 proxy or fallback will be used. Commercial approval and live validation remain the owner's responsibility.")
        yield ElimCollector(settings, config.max_products, log=log, result_allowance=allowance)
        return
    proxy = await browser_proxy(config, log)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, proxy=proxy)
        context = await browser.new_context()
        try:
            yield BrowserCollector(context, on_failure=on_failure, log=log)
        finally:
            await context.close()
            await browser.close()


async def main():
    async with Actor:
        config = Config.parse(await Actor.get_input())
        Actor.log.warning(f"Development build {__version__}: keyword and Offer ID parsers are fixture-tested, but live 1688 collection is NOT release-validated.")
        Actor.log.info(f"Selected input: {config.mode}. Offer IDs take priority over keywords.")
        async def checkpoint(products, summary):
            await Actor.set_value("PARTIAL_RESULTS.json", products)
            await Actor.set_value("RUN_SUMMARY.json", summary)
        async def on_failure(key, report):
            await Actor.set_value(key, report)
            Actor.log.warning(f"Collection failed at {report['stage']}: {report['error_code']}. Saved {key} in the key-value store.")
        runner = None
        try:
            async with collection_backend(config, on_failure, Actor.log.info) as collector:
                runner = Runner(config, collector, checkpoint)
                if isinstance(collector, ElimCollector):
                    runner.summary["notes"].append("Elim provider API prices may differ from website prices; currency/tier mapping and live access are not validated. Provider charges are billed separately to the owner.")
                await runner.run()
        finally:
            if runner is not None:
                products = list(runner.products.values())
                # One final dataset record per product, including all matched inputs.
                # Page checkpoints in KVS retain progress if a hard timeout prevents this.
                if products:
                    await Actor.push_data(products)
                if config.save_csv:
                    await Actor.set_value(config.csv_filename, csv_text(products), content_type="text/csv; charset=utf-8")
                    await Actor.set_value("1688_suppliers.csv", csv_text(supplier_rows(products), SUPPLIER_FIELDS), content_type="text/csv; charset=utf-8")
                await runner.save()


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        Config.parse({})
        print(f"1688 Actor {__version__}: imports and default input valid; no target requests made.")
    else:
        asyncio.run(main())
