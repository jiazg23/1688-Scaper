"""Ordinary browser interaction using supplied DOM selectors.

Development tests use saved HTML; successful live collection is not established.
There is no stealth browser, alternate API, CAPTCHA solver, imported login or
identity switching after an access denial.
"""

import asyncio

from playwright.async_api import Error as BrowserError, TimeoutError as BrowserTimeout

from .config import product_url
from .diagnostics import capture_failure
from .popups import LOGIN_FRAME, dismiss_optional_login, is_login_url
from .parser import (CARD, NEXT, KEYWORD, SEARCH, AccessBlocked, CollectionError,
                     UnsupportedLayout, check_access, check_http_status, parse_search, parse_product)

HOME = "https://www.1688.com/"


async def guard_page(page):
    signals = {"verification_element": False, "login_form": False}
    for element in await page.locator('#nc_1_wrapper, #baxia-dialog-content, iframe[src*="punish"], iframe[src*="captcha"]').all():
        if await element.is_visible():
            signals["verification_element"] = True
            break
    # Check actual verification and full-page sign-in redirects before attempting
    # to close any optional UI. Never navigate away to circumvent these checks.
    check_access(await page.content(), page.url, visible_signals=signals)
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        if any(token in frame.url.lower() for token in ("_____tmd_____", "/punish", "captcha")):
            element = await frame.frame_element()
            if await element.is_visible():
                raise AccessBlocked("1688 presented a visible verification frame. Collection stopped.", "verification_frame")
    await dismiss_optional_login(page)
    for iframe in await page.locator(LOGIN_FRAME).all():
        if await iframe.is_visible():
            raise AccessBlocked("The alibaba-login-box popup remains visible. Its surrounding X/close-control markup is needed.", "login_popup_close_missing")
    for element in await page.locator('input[type=password]').all():
        if await element.is_visible():
            signals["login_form"] = True
            break
    check_access(await page.content(), page.url, visible_signals=signals)
    for frame in page.frames:
        if frame != page.main_frame and is_login_url(frame.url):
            element = await frame.frame_element()
            if await element.is_visible():
                raise AccessBlocked("A login frame remains visible and could not be dismissed normally.", "login_frame")
    return signals


async def wait_results(page, timeout_seconds=45, popup_pages=None, baseline_ids=None):
    """Follow a search popup or same-tab result; never mistake home cards for results."""
    popup_pages = popup_pages if popup_pages is not None else []
    for _ in range(timeout_seconds * 2):
        ready, optional_login_tabs = None, []
        for candidate in [page, *list(popup_pages)]:
            if candidate.is_closed():
                continue
            try:
                await guard_page(candidate)
                ids = set(await candidate.locator(CARD).evaluate_all("nodes => nodes.map(n => n.dataset.offerid)"))
                if ids and (candidate != page or baseline_ids is None or ids != baseline_ids):
                    if await candidate.locator(CARD).first.is_visible():
                        ready = candidate
            except AccessBlocked as error:
                error.source_page = candidate
                # Only a separately opened login tab may be optional, and only
                # when a different tab has already exposed usable public results.
                if candidate != page and error.code == "login_url":
                    optional_login_tabs.append((candidate, error))
                else:
                    raise
            except BrowserError:
                # A newly created popup can still be navigating. Observe it;
                # do not issue a retry, change identities, or guess a result URL.
                continue
        if ready is not None:
            for login_tab, _ in optional_login_tabs:
                await login_tab.close()
            return ready
        if optional_login_tabs:
            raise optional_login_tabs[0][1]
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


async def wait_product(page, expected_url, timeout_seconds=45):
    """Wait for a source-backed detail record for this exact offer, not a recommendation."""
    for _ in range(timeout_seconds * 2):
        signals = await guard_page(page)
        try:
            return parse_product(await page.content(), expected_url, visible_signals=signals)
        except UnsupportedLayout:
            await asyncio.sleep(0.5)
    raise CollectionError("No supported, identity-matched product details appeared within the time limit.")


class BrowserCollector:
    def __init__(self, context, on_failure=None, log=None):
        self.context = context
        self.on_failure = on_failure
        self.log = log

    async def pages(self, spec, max_pages):
        if spec["kind"] not in {"keyword", "offer_ids"}:
            raise CollectionError("Only keyword and Offer ID inputs are supported.")
        page = await self.context.new_page()
        owned_pages = [page]
        popup_pages = []
        def on_popup(popup):
            popup_pages.append(popup)
            owned_pages.append(popup)
        page.on("popup", on_popup)
        page.set_default_timeout(30000)
        stage, http_status = "initializing_browser_page", None
        def progress(value):
            nonlocal stage
            stage = value
            if self.log:
                self.log(f"[{spec['kind'].upper()} {spec['index']}] Stage: {stage}")
        try:
            if spec["kind"] == "offer_ids":
                expected_url = product_url(spec["value"])
                progress("opening_offer")
                response = await page.goto(expected_url, wait_until="domcontentloaded", timeout=45000)
                http_status = response.status if response else None
                check_http_status(http_status)
                await guard_page(page)
                if response and response.status >= 400:
                    raise CollectionError(f"Product page returned HTTP {response.status}.")
                progress("waiting_for_offer")
                product = await wait_product(page, expected_url)
                progress("reading_offer")
                yield {"products": [product], "has_next": False, "page_number": 1}
                return
            progress("opening_homepage")
            if self.log:
                self.log(f"Opening the public homepage: {HOME}")
            response = await page.goto(HOME, wait_until="domcontentloaded", timeout=45000)
            http_status = response.status if response else None
            check_http_status(http_status)
            await guard_page(page)
            if response and response.status >= 400:
                raise CollectionError(f"1688 home page returned HTTP {response.status}.")
            baseline_ids = set(await page.locator(CARD).evaluate_all("nodes => nodes.map(n => n.dataset.offerid)"))
            progress("entering_keyword")
            await page.locator(KEYWORD).first.fill(spec["value"])
            progress("submitting_keyword")
            await page.locator(SEARCH).first.click()
            progress("waiting_for_results")
            source_page = page
            page = await wait_results(source_page, popup_pages=popup_pages, baseline_ids=baseline_ids)
            if page != source_page and self.log:
                self.log("Search opened a new tab; collecting from that results tab.")
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
                await capture_failure(getattr(error, "source_page", page), spec, stage, error, self.on_failure, http_status)
                raise error from None
            except Exception:
                pass  # The page may be closing/navigating; still save the timeout stage.
            error = CollectionError(f"A 1688 browser action timed out at {stage}; inspect the failure report.")
            await capture_failure(page, spec, stage, error, self.on_failure, http_status)
            raise error from None
        except Exception as error:
            await capture_failure(getattr(error, "source_page", page), spec, stage, error, self.on_failure, http_status)
            raise
        finally:
            for owned in reversed(owned_pages):
                if not owned.is_closed():
                    await owned.close()
