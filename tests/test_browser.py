"""Offline browser tests. All network requests are aborted before loading fixtures."""

from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.collector import guard_page, next_page, wait_results
from src.parser import (CARD, KEYWORD, SEARCH, IMAGE_OPEN, IMAGE_INPUT, IMAGE_CONFIRM,
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

    async def test_real_saved_search_and_upload_selectors(self):
        await self.page.set_content((FIXTURES / "search-controls.html").read_text())
        await self.page.locator(KEYWORD).fill("hair dryer")
        self.assertEqual(await self.page.locator(KEYWORD).input_value(), "hair dryer")
        self.assertEqual(await self.page.locator(SEARCH).count(), 1)
        self.assertEqual(await self.page.locator(IMAGE_OPEN).count(), 1)
        await self.page.evaluate("""() => {
            document.querySelector('.cgf-search-input__image-btn').onclick = () => {
                document.querySelector('.cgf-image-search-popover').style.display = 'block';
            };
            document.querySelector('input[type=file]').onchange = () => {
                document.querySelector('.cgf-image-search-panel__confirm-btn').disabled = false;
            };
        }""")
        await self.page.locator(IMAGE_OPEN).click()
        await self.page.locator(IMAGE_INPUT).set_input_files({"name": "fixture.png", "mimeType": "image/png", "buffer": b"\x89PNG\r\n\x1a\n"})
        self.assertTrue(await self.page.locator(IMAGE_CONFIRM).is_enabled())
        self.assertEqual(await self.page.locator(IMAGE_INPUT).evaluate("e => e.files.length"), 1)

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


if __name__ == "__main__":
    unittest.main()
