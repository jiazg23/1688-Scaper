"""Apify entrypoint. Import/startup checks never contact the target website."""

import asyncio
import sys
from urllib.parse import unquote, urlsplit

from apify import Actor
from playwright.async_api import async_playwright

from . import __version__
from .collector import BrowserCollector
from .config import Config
from .exports import csv_text, supplier_rows, SUPPLIER_FIELDS
from .runner import Runner


async def main():
    async with Actor:
        config = Config.parse(await Actor.get_input())
        Actor.log.warning("Development build: selectors are fixture-tested, but live 1688 access, uploads and detail pages are NOT release-validated.")
        proxy = None
        if config.use_proxy:
            proxy_config = await Actor.create_proxy_configuration()
            if proxy_config is None:
                raise RuntimeError("Apify Proxy was enabled but is unavailable. Configure access or explicitly disable it for a permitted direct run.")
            proxy_url = await proxy_config.new_url()
            parts = urlsplit(proxy_url)
            proxy = {"server": f"{parts.scheme}://{parts.hostname}:{parts.port}",
                     "username": unquote(parts.username or ""), "password": unquote(parts.password or "")}
        async def checkpoint(products, summary):
            await Actor.set_value("PARTIAL_RESULTS.json", products)
            await Actor.set_value("RUN_SUMMARY.json", summary)
        runner = None
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True, proxy=proxy)
                context = await browser.new_context()
                try:
                    runner = Runner(config, BrowserCollector(context), checkpoint)
                    await runner.run()
                finally:
                    await context.close()
                    await browser.close()
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
