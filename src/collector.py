"""Ordinary browser interaction using supplied DOM selectors.

This module has NOT been run against live 1688 during development. There is no
stealth browser, alternate API, CAPTCHA solver, imported login, or proxy rotation.
"""

import asyncio

from playwright.async_api import TimeoutError as BrowserTimeout

from .images import download_image
from .diagnostics import capture_failure
from .parser import (CARD, NEXT, KEYWORD, SEARCH, IMAGE_OPEN, IMAGE_INPUT, IMAGE_CONFIRM,
                     AccessBlocked, CollectionError, check_access, check_http_status, parse_search, parse_product)

HOME = "https://www.1688.com/"


async def guard_page(page):
    signals = {"verification_element": False, "login_form": False}
    for key, selector in (("verification_element", '#nc_1_wrapper, #baxia-dialog-content, iframe[src*="punish"], iframe[src*="captcha"]'),
                          ("login_form", 'input[type=password]')):
        for element in await page.locator(selector).all():
            if await element.is_visible():
                signals[key] = True
                break
    check_access(await page.content(), page.url, visible_signals=signals)
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        if any(token in frame.url.lower() for token in ("_____tmd_____", "/punish", "captcha", "login.1688.com")):
            element = await frame.frame_element()
            if await element.is_visible():
                raise AccessBlocked("1688 presented a visible verification/sign-in frame. Collection stopped.", "verification_frame")
    return signals


async def wait_results(page, timeout_seconds=45):
    for _ in range(timeout_seconds * 2):
        await guard_page(page)
        if await page.locator(CARD).count():
            return
        await asyncio.sleep(0.5)
    raise CollectionError("No supported result cards appeared within 45 seconds; access or layout needs checking.")


async def next_page(page, before):
    """A button click is insufficient: product IDs and page indicator must change."""
    button = page.locator(NEXT).first
    if not await button.count():
        raise CollectionError("Pagination control is missing; cannot verify that all pages were processed.")
    if not await button.is_enabled() or await button.get_attribute("aria-disabled") == "true":
        return False
    await button.click(timeout=15000)
    old_ids = {p["product_id"] for p in before["products"]}
    for _ in range(90):
        signals = await guard_page(page)
        try:
            after = parse_search(await page.content(), page.url, visible_signals=signals)
        except AccessBlocked:
            raise
        except CollectionError:
            await asyncio.sleep(0.5)
            continue
        new_ids = {p["product_id"] for p in after["products"]}
        old_number, new_number = before["page_number"], after["page_number"]
        # Do not accept just a new page label while old cards remain on screen.
        if new_ids - old_ids and (old_number is None or new_number is None or new_number > old_number):
            return True
        await asyncio.sleep(0.5)
    raise CollectionError("Next page did not produce new product cards; stopped to avoid repeating page 1.")


class BrowserCollector:
    def __init__(self, context, on_failure=None, log=None):
        self.context = context
        self.on_failure = on_failure
        self.log = log

    async def pages(self, spec, max_pages):
        page = await self.context.new_page()
        page.set_default_timeout(30000)
        stage, http_status = "initializing_browser_page", None
        def progress(value):
            nonlocal stage
            stage = value
            if self.log:
                self.log(f"[{spec['kind'].upper()} {spec['index']}] Stage: {stage}")
        try:
            if spec["kind"] == "urls":
                progress("opening_product")
                response = await page.goto(spec["value"], wait_until="domcontentloaded", timeout=45000)
                http_status = response.status if response else None
                check_http_status(http_status)
                await guard_page(page)
                if response and response.status >= 400:
                    raise CollectionError(f"Product page returned HTTP {response.status}.")
                product = None
                progress("reading_product_details")
                for _ in range(90):
                    signals = await guard_page(page)
                    try:
                        product = parse_product(await page.content(), spec["value"], visible_signals=signals)
                        break
                    except AccessBlocked:
                        raise
                    except CollectionError:
                        pass
                    await asyncio.sleep(0.5)
                if product is None:
                    raise CollectionError("No supported, identity-matched product details loaded within 45 seconds.")
                yield {"products": [product], "has_next": False, "page_number": 1}
                return
            # Image download happens first, so a bad image does not make a site request.
            payload = None
            if spec["kind"] == "image":
                progress("downloading_image")
                data, mime = await asyncio.to_thread(download_image, spec["value"])
                payload = {"name": "product." + {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[mime],
                           "mimeType": mime, "buffer": data}
            progress("opening_homepage")
            response = await page.goto(HOME, wait_until="domcontentloaded", timeout=45000)
            http_status = response.status if response else None
            check_http_status(http_status)
            await guard_page(page)
            if response and response.status >= 400:
                raise CollectionError(f"1688 home page returned HTTP {response.status}.")
            if spec["kind"] == "keyword":
                progress("entering_keyword")
                await page.locator(KEYWORD).first.fill(spec["value"])
                progress("submitting_keyword")
                await page.locator(SEARCH).first.click()
            else:
                progress("uploading_image")
                await page.locator(IMAGE_OPEN).first.click()
                await page.locator(IMAGE_INPUT).first.set_input_files(payload)
                await page.locator(IMAGE_CONFIRM).first.click()
            # The supplied markup does not establish popup behavior. Do not guess
            # URLs or use alternative endpoints if same-page results never arrive.
            progress("waiting_for_results")
            await wait_results(page)
            signatures = set()
            for _ in range(max_pages):
                progress("reading_results")
                signals = await guard_page(page)
                result = parse_search(await page.content(), page.url, visible_signals=signals)
                signature = tuple(sorted(p["product_id"] for p in result["products"]))
                if signature in signatures:
                    raise CollectionError("Repeated results page detected; pagination is not progressing.")
                signatures.add(signature)
                yield result
                if result["has_next"] is False:
                    return
                if result["has_next"] is None:
                    raise CollectionError("Product cards were collected, but pagination markup is missing. Run is partial.")
                if len(signatures) < max_pages:
                    progress("opening_next_page")
                    if not await next_page(page, result):
                        return
        except BrowserTimeout:
            # Avoid copying verbose browser trace URLs or tokens into logs.
            try:
                await guard_page(page)
            except AccessBlocked as error:
                await capture_failure(page, spec, stage, error, self.on_failure, http_status)
                raise error from None
            except Exception:
                pass  # The page may be closing/navigating; still save the timeout stage.
            error = CollectionError(f"A 1688 browser action timed out at {stage}; inspect the failure report.")
            await capture_failure(page, spec, stage, error, self.on_failure, http_status)
            raise error from None
        except Exception as error:
            await capture_failure(page, spec, stage, error, self.on_failure, http_status)
            raise
        finally:
            if not page.is_closed():
                await page.close()
