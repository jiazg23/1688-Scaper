"""Offline browser tests. All network requests are aborted before loading fixtures."""

from pathlib import Path
from contextlib import aclosing
import unittest
from unittest.mock import AsyncMock, patch

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.collector import HOME, BrowserCollector, guard_page, next_page, wait_results, wait_product
from src.popups import dismiss_optional_login
from src.parser import (CARD, KEYWORD, SEARCH,
                        parse_search, CollectionError, AccessBlocked)

FIXTURES = Path(__file__).parent / "fixtures"


class OfflineBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.blocked_requests = []
        async def block(route):
            self.blocked_requests.append(route.request.url)
            await route.abort()
        await self.context.route("**/*", block)
        self.page = await self.context.new_page()
        source = BeautifulSoup((FIXTURES / "search-results.html").read_text(), "html.parser")
        self.card = str(source.select_one(CARD))
        self.pagination = (FIXTURES / "pagination.html").read_text()

    async def asyncTearDown(self):
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    async def test_real_saved_keyword_controls(self):
        await self.page.set_content((FIXTURES / "search-controls.html").read_text())
        await self.page.locator(KEYWORD).fill("wireless earbuds")
        self.assertEqual(await self.page.locator(KEYWORD).input_value(), "wireless earbuds")
        self.assertEqual(await self.page.locator(SEARCH).count(), 1)

    async def test_pagination_requires_changed_products(self):
        await self.page.set_content(self.card + self.pagination)
        before = parse_search(await self.page.content())
        await self.page.evaluate("""() => {
            document.querySelector('.cgf-sale-pagination-next').onclick = () => {
                document.querySelector('[data-offerid]').dataset.offerid = '999999999999';
                document.querySelector('.cgf-sale-pagination-page-active').textContent = '2';
            };
        }""")
        self.assertTrue(await next_page(self.page, before))
        self.assertEqual(parse_search(await self.page.content())["products"][0]["product_id"], "999999999999")

    async def test_disabled_next_stops(self):
        await self.page.set_content(self.card + self.pagination.replace('class="cgf-sale-pagination-next"', 'disabled class="cgf-sale-pagination-next"'))
        self.assertFalse(await next_page(self.page, parse_search(await self.page.content())))

    async def test_page_number_alone_not_accepted(self):
        await self.page.set_content(self.card + self.pagination)
        before = parse_search(await self.page.content())
        await self.page.evaluate("""() => {
            document.querySelector('.cgf-sale-pagination-next').onclick = () => {
                document.querySelector('.cgf-sale-pagination-page-active').textContent = '2';
            };
        }""")
        with patch("src.collector.asyncio.sleep", new=AsyncMock()):
            with self.assertRaises(CollectionError):
                await next_page(self.page, before)

    async def test_verification_is_terminal(self):
        await self.page.set_content('<title>安全验证</title><main>verification</main>')
        with self.assertRaises(AccessBlocked):
            await wait_results(self.page, timeout_seconds=1)

    async def test_css_hidden_login_and_script_reference_are_not_blocked(self):
        await self.page.set_content('<title>1688</title><style>.login-popup {display:none}</style><div class="login-popup"><input type=password></div><textarea class="cgf-search-input__input"></textarea><script>const reference="/_____tmd_____/punish";</script>')
        signals = await guard_page(self.page)
        self.assertFalse(signals["login_form"])

    async def test_active_login_is_still_blocked(self):
        await self.page.set_content('<form><input type=password></form>')
        with self.assertRaises(AccessBlocked):
            await guard_page(self.page)

    async def test_configured_homepage_is_exact_public_url(self):
        self.assertEqual(HOME, "https://www.1688.com/")

    async def test_keyword_results_can_open_in_a_new_tab(self):
        await self.page.set_content((FIXTURES / "search-controls.html").read_text())
        pages = []
        self.page.on("popup", lambda popup: pages.append(popup))
        async with self.page.expect_popup() as pending:
            await self.page.evaluate("window.open('about:blank', '_blank')")
        result_page = await pending.value
        await result_page.set_content(self.card + self.pagination, wait_until="domcontentloaded")
        selected = await wait_results(self.page, popup_pages=pages, timeout_seconds=1, baseline_ids=set())
        self.assertEqual(selected, result_page)
        self.assertEqual(len(parse_search(await selected.content())["products"]), 1)

    async def test_same_tab_results_remain_supported(self):
        await self.page.set_content(self.card + self.pagination)
        self.assertEqual(await wait_results(self.page, timeout_seconds=1, baseline_ids=set()), self.page)

    async def test_unchanged_homepage_cards_are_not_search_results(self):
        await self.page.set_content(self.card)
        old_ids = {parse_search(self.card)["products"][0]["product_id"]}
        with patch("src.collector.asyncio.sleep", new=AsyncMock()):
            with self.assertRaises(CollectionError):
                await wait_results(self.page, timeout_seconds=1, baseline_ids=old_ids)

    async def test_known_login_iframe_is_closed_with_its_x(self):
        iframe = (FIXTURES / "login-iframe.html").read_text()
        await self.page.set_content('<textarea class="cgf-search-input__input"></textarea><div role="dialog" aria-label="Login"><button aria-label="Close" onclick="this.parentElement.remove()">×</button>' + iframe + '</div>')
        signals = await guard_page(self.page)
        self.assertFalse(signals["login_form"])
        self.assertEqual(await self.page.locator("#alibaba-login-box").count(), 0)
        self.assertTrue(await self.page.locator(KEYWORD).is_visible())

    async def test_visible_optional_password_dialog_is_closed(self):
        await self.page.set_content('<textarea class="cgf-search-input__input"></textarea><div role="dialog"><h2>Sign in</h2><input type=password><button onclick="this.parentElement.remove()">Close</button></div>')
        await guard_page(self.page)
        self.assertEqual(await self.page.locator('input[type=password]').count(), 0)

    async def test_login_iframe_without_close_control_is_not_removed(self):
        iframe = (FIXTURES / "login-iframe.html").read_text()
        await self.page.set_content('<textarea class="cgf-search-input__input"></textarea><div role="dialog" aria-label="Login">' + iframe + '</div>')
        with self.assertRaises(AccessBlocked) as raised:
            await guard_page(self.page)
        self.assertEqual(raised.exception.code, "login_popup_close_missing")
        self.assertEqual(await self.page.locator("#alibaba-login-box").count(), 1)

    async def test_login_without_public_content_is_not_dismissed(self):
        await self.page.set_content('<div role="dialog"><h2>Sign in</h2><input type=password><button onclick="this.parentElement.remove()">Close</button></div>')
        self.assertFalse(await dismiss_optional_login(self.page))
        with self.assertRaises(AccessBlocked):
            await guard_page(self.page)
        self.assertEqual(await self.page.get_by_role("dialog").count(), 1)

    async def test_verification_dialog_is_not_dismissed(self):
        await self.page.set_content('<textarea class="cgf-search-input__input"></textarea><div role="dialog" id="nc_1_wrapper"><h2>Sign in — CAPTCHA</h2><button onclick="this.parentElement.remove()">Close</button></div>')
        with self.assertRaises(AccessBlocked):
            await guard_page(self.page)
        self.assertEqual(await self.page.locator("#nc_1_wrapper").count(), 1)

    async def test_nonworking_close_does_not_allow_collection(self):
        iframe = (FIXTURES / "login-iframe.html").read_text()
        await self.page.set_content('<textarea class="cgf-search-input__input"></textarea><div role="dialog" aria-label="Login"><button aria-label="Close">×</button>' + iframe + '</div>')
        with self.assertRaises(AccessBlocked) as raised:
            await guard_page(self.page)
        self.assertEqual(raised.exception.code, "login_popup_not_dismissed")

    async def test_offer_id_opens_only_its_public_detail_page(self):
        url = "https://detail.1688.com/offer/1071313125369.html"
        async def load_fixture(target, **kwargs):
            await self.page.set_content((FIXTURES / "product-detail.html").read_text(), wait_until="domcontentloaded")
            return type("Response", (), {"status": 200})()
        with patch.object(self.context, "new_page", new=AsyncMock(return_value=self.page)), patch.object(self.page, "goto", new=AsyncMock(side_effect=load_fixture)) as navigation:
            collector = BrowserCollector(self.context)
            async with aclosing(collector.pages({"index": 1, "kind": "offer_ids", "value": "1071313125369"}, 5)) as pages:
                batch = await anext(pages)
                self.assertFalse(batch["has_next"])
                self.assertEqual(batch["products"][0]["product_id"], "1071313125369")
                with self.assertRaises(StopAsyncIteration):
                    await anext(pages)
            navigation.assert_awaited_once_with(url, wait_until="domcontentloaded", timeout=45000)

    async def test_offer_wait_requires_matching_identity(self):
        await self.page.set_content((FIXTURES / "product-detail.html").read_text(), wait_until="domcontentloaded")
        with patch("src.collector.asyncio.sleep", new=AsyncMock()):
            with self.assertRaises(CollectionError):
                await wait_product(self.page, "https://detail.1688.com/offer/999999999999.html", timeout_seconds=1)

    async def test_verification_on_offer_remains_terminal_and_diagnostic(self):
        async def load_verification(target, **kwargs):
            await self.page.set_content("<title>安全验证</title>", wait_until="domcontentloaded")
            return type("Response", (), {"status": 200})()
        failure = AsyncMock()
        with patch.object(self.context, "new_page", new=AsyncMock(return_value=self.page)), patch.object(self.page, "goto", new=AsyncMock(side_effect=load_verification)) as navigation:
            collector = BrowserCollector(self.context, on_failure=failure)
            async with aclosing(collector.pages({"index": 1, "kind": "offer_ids", "value": "1071313125369"}, 1)) as pages:
                with self.assertRaises(AccessBlocked):
                    await anext(pages)
            self.assertEqual(navigation.await_count, 1)
        report = failure.call_args.args[1]
        self.assertEqual(report["stage"], "opening_offer")
        self.assertEqual(report["error_code"], "verification_title")

    async def test_removed_modes_do_not_open_any_browser_page(self):
        for kind in ["image", "search_urls", "urls"]:
            with self.subTest(kind=kind), patch.object(self.context, "new_page", new=AsyncMock()) as opening:
                async with aclosing(BrowserCollector(self.context).pages({"kind": kind, "value": "unused", "index": 1}, 1)) as pages:
                    with self.assertRaises(CollectionError):
                        await anext(pages)
                opening.assert_not_awaited()

    async def test_keyword_collector_submits_input_and_reads_next_page(self):
        async def load_home(target, **kwargs):
            await self.page.set_content((FIXTURES / "search-controls.html").read_text(), wait_until="domcontentloaded")
            await self.page.evaluate("""(results) => {
                document.querySelector('button[data-tracker="textSearch.search"]').onclick = () => {
                    window.submittedKeyword = document.querySelector('textarea.cgf-search-input__input').value;
                    document.body.innerHTML = results;
                    document.querySelector('.cgf-sale-pagination-next').onclick = () => {
                        document.querySelector('[data-offerid]').dataset.offerid = '999999999999';
                        document.querySelector('.cgf-sale-pagination-page-active').textContent = '2';
                        document.querySelector('.cgf-sale-pagination-next').disabled = true;
                    };
                };
            }""", self.card + self.pagination)
            return type("Response", (), {"status": 200})()
        with patch.object(self.context, "new_page", new=AsyncMock(return_value=self.page)), patch.object(self.page, "goto", new=AsyncMock(side_effect=load_home)) as navigation:
            collector = BrowserCollector(self.context)
            async with aclosing(collector.pages({"kind": "keyword", "value": "wireless earbuds", "index": 1}, 3)) as pages:
                first = await anext(pages)
                second = await anext(pages)
                self.assertNotEqual(first["products"][0]["product_id"], second["products"][0]["product_id"])
                self.assertEqual(second["page_number"], 2)
                self.assertFalse(second["has_next"])
                self.assertEqual(await self.page.evaluate("window.submittedKeyword"), "wireless earbuds")
                with self.assertRaises(StopAsyncIteration):
                    await anext(pages)
            navigation.assert_awaited_once_with(HOME, wait_until="domcontentloaded", timeout=45000)


if __name__ == "__main__":
    unittest.main()
