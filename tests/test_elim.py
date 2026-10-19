"""All Elim responses/transports are synthetic. No credentials or live requests."""

import asyncio
import io
import json
import unittest
from contextlib import aclosing
from email.message import Message
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from urllib.error import HTTPError, URLError

from src.config import Config, InputError
from src.elim import (ElimSettings, ElimClient, ElimCollector, ProviderError,
                      NoRedirect, data_source, normalize_product, MAX_BODY_BYTES)
from src.main import collection_backend
from src.runner import Runner, RunFailed


def owner_env(**overrides):
    return {"PRODUCT_DATA_SOURCE": "elim", "ELIM_COMMERCIAL_USE_APPROVED": "true",
            "ELIM_API_KEY": "TEST-KEY-NOT-A-REAL-SECRET", **overrides}


def product(identity="1071313125369", **extra):
    return {"id": identity, "title": "Synthetic hair dryer", "price": "25.00",
            "shop_id": "shop-test", "shop_name": "Synthetic supplier", "moq": 2,
            "img_urls": ["https://example.test/product.jpg"], **extra}


def result(items, page=1, size=20, total=None):
    return {"items": items, "paginate": {"current": page, "size": size,
                                         "total": len(items) if total is None else total}}


def collector(responses, *, limit=5, max_products=100, allowance=None):
    client = SimpleNamespace(post=AsyncMock(side_effect=responses))
    return ElimCollector(ElimSettings("test", limit), max_products, client=client,
                         result_allowance=allowance, sleep=AsyncMock()), client


class ProviderSetupTests(unittest.TestCase):
    def test_disabled_by_default_and_no_unknown_fallback(self):
        self.assertEqual(data_source({}), "browser")
        with self.assertRaises(InputError):
            data_source({"PRODUCT_DATA_SOURCE": "unknown"})

    def test_permission_and_key_required(self):
        for env in [{}, {"ELIM_API_KEY": "test"}, {"ELIM_COMMERCIAL_USE_APPROVED": "true"}]:
            with self.subTest(env=env), self.assertRaises(InputError):
                ElimSettings.from_env(env)

    def test_secret_not_represented_or_reflected_in_errors(self):
        self.assertNotIn("TEST-KEY", repr(ElimSettings.from_env(owner_env())))
        for key in ["TEST-KEY\nheader", " TEST-KEY", "TEST-KEY ", "é"]:
            with self.assertRaises(InputError) as raised:
                ElimSettings.from_env(owner_env(ELIM_API_KEY=key))
            self.assertNotIn(key, str(raised.exception))

    def test_owner_request_cap_cannot_be_unlimited(self):
        self.assertEqual(ElimSettings.from_env(owner_env()).max_requests, 5)
        for value in ["0", "101", "-1", "unlimited", "1.0"]:
            with self.subTest(value=value), self.assertRaises(InputError):
                ElimSettings.from_env(owner_env(ELIM_MAX_REQUESTS_PER_RUN=value))

    def test_unpaid_and_unknown_plan_are_off_by_default(self):
        for paying in ["false", "", "unknown"]:
            with self.subTest(paying=paying), self.assertRaises(InputError):
                ElimSettings.from_env(owner_env(APIFY_IS_AT_HOME="1", APIFY_USER_IS_PAYING=paying))
        ElimSettings.from_env(owner_env(APIFY_IS_AT_HOME="1", APIFY_USER_IS_PAYING="true"))
        ElimSettings.from_env(owner_env(APIFY_IS_AT_HOME="1", ELIM_ALLOW_UNPAID_RUNS="true"))

    def test_only_allowlisted_fields_are_exported(self):
        item = normalize_product(product(secret="DO-NOT-EXPORT", description="SECRET-HTML", skus=[{"private": "SECRET"}], currency="USD"))
        self.assertNotIn("SECRET", json.dumps(item))
        self.assertIsNone(item["currency"])
        self.assertEqual(item["display_price"], "25.00")
        self.assertEqual(item["price_tiers"], [])
        self.assertIsNone(item["verified_supplier"])
        self.assertIsNone(item["manufacturer"])
        self.assertIn("may differ", item["price_context"])

    def test_identity_and_title_are_required(self):
        for item in [None, {}, product(True), product("not-id"), product(title="")]:
            with self.subTest(item=item), self.assertRaises(ProviderError):
                normalize_product(item)
        with self.assertRaises(ProviderError):
            normalize_product(product(), expected_id="999999999999")

    def test_unknown_nested_fields_and_bad_values_do_not_fabricate_claims(self):
        item = normalize_product(product(price={"from": 10}, moq=True, seller_type={"factory": True},
                                         img_urls=["javascript:alert(1)", "https://user:secret@example.test/x", None]))
        self.assertIsNone(item["display_price"])
        self.assertIsNone(item["moq"])
        self.assertIsNone(item["provider_seller_type"])
        self.assertIsNone(item["image_url"])


class TransportTests(unittest.TestCase):
    def response(self, body=b"{}", *, status=200, content_type="application/json"):
        headers = Message()
        headers["Content-Type"] = content_type
        response = Mock(status=status, headers=headers)
        response.read.return_value = body
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        return context

    def test_https_key_header_and_disabled_redirect_and_proxy(self):
        opener = Mock()
        opener.open.return_value = self.response(b'{"items":[]}')
        with patch("src.elim.build_opener", return_value=opener) as build:
            ElimClient(ElimSettings("SECRET"))._post("/v2/products/search", {"platform": "alibaba"})
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://openapi.elim.asia/v2/products/search")
        self.assertEqual(request.get_header("X-api-key"), "SECRET")
        self.assertEqual(build.call_args.args[0].proxies, {})
        self.assertIsInstance(build.call_args.args[1], NoRedirect)
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.test"))

    def test_non_allowlisted_endpoint_never_opens_network(self):
        with patch("src.elim.build_opener") as build, self.assertRaises(ProviderError):
            ElimClient(ElimSettings("SECRET"))._post("https://other.test/", {})
        build.assert_not_called()

    def test_http_error_is_sanitized_and_not_retried(self):
        for status in [302, 400, 401, 403, 429, 500]:
            opener = Mock()
            opener.open.side_effect = HTTPError("https://example.test/?secret=SECRET", status, "SECRET", {}, io.BytesIO(b"SECRET"))
            with self.subTest(status=status), patch("src.elim.build_opener", return_value=opener), self.assertRaises(ProviderError) as raised:
                ElimClient(ElimSettings("SECRET"))._post("/v2/products/find", {})
            self.assertNotIn("SECRET", str(raised.exception))
            self.assertEqual(raised.exception.code, f"provider_http_{status}")
            self.assertEqual(opener.open.call_count, 1)

    def test_transport_json_type_and_size_errors_are_sanitized(self):
        for response in [self.response(b"SECRET"), self.response(b"[]"),
                         self.response(content_type="text/html"), self.response(b"x" * (MAX_BODY_BYTES + 1))]:
            opener = Mock()
            opener.open.return_value = response
            with patch("src.elim.build_opener", return_value=opener), self.assertRaises(ProviderError) as raised:
                ElimClient(ElimSettings("SECRET"))._post("/v2/products/find", {})
            self.assertNotIn("SECRET", str(raised.exception))
        opener.open.side_effect = URLError("SECRET")
        with patch("src.elim.build_opener", return_value=opener), self.assertRaises(ProviderError) as raised:
            ElimClient(ElimSettings("SECRET"))._post("/v2/products/find", {})
        self.assertNotIn("SECRET", str(raised.exception))


class ProviderWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_keyword_pagination_contract(self):
        c, client = collector([result([product()], total=21), result([product("999999999999")], page=2, total=21)])
        batches = [batch async for batch in c.pages({"kind": "keyword", "value": "Hair dryer"}, 5)]
        self.assertEqual(len(batches), 2)
        self.assertTrue(batches[0]["has_next"])
        self.assertFalse(batches[1]["has_next"])
        self.assertEqual(client.post.call_args_list[1].args[1], {"platform": "alibaba", "q": "Hair dryer", "page": 2, "size": 40})
        c.sleep.assert_awaited_once()

    async def test_id_skips_keyword_search_and_matches_identity(self):
        c, client = collector([product()])
        batches = [batch async for batch in c.pages({"kind": "offer_ids", "value": "1071313125369"}, 5)]
        self.assertEqual(batches[0]["products"][0]["product_id"], "1071313125369")
        client.post.assert_awaited_once_with("/v2/products/find", {"platform": "alibaba", "id": "1071313125369"})

    async def test_missing_metadata_preserves_page_without_claiming_exhaustion(self):
        c, _ = collector([{"items": [product()]}])
        async with aclosing(c.pages({"kind": "keyword", "value": "test"}, 5)) as pages:
            batch = await anext(pages)
            self.assertIsNone(batch["has_next"])
            with self.assertRaises(ProviderError) as raised:
                await anext(pages)
        self.assertEqual(raised.exception.code, "provider_pagination_missing")

    async def test_request_cap_is_shared_across_keywords_and_preserves_export(self):
        c, client = collector([result([product()])], limit=1)
        runner = Runner(Config.parse({"keywords": ["one", "two", "three"]}), c, AsyncMock())
        with self.assertRaises(RunFailed):
            await runner.run()
        self.assertEqual(len(runner.products), 1)
        self.assertEqual(client.post.await_count, 1)
        self.assertEqual(runner.summary["provider_requests_attempted"], 1)
        self.assertEqual(runner.summary["inputs"][2]["status"], "not_started")

    async def test_failed_attempt_counts_and_is_not_retried_or_fallback(self):
        c, client = collector([ProviderError("Rate limit", "provider_http_429")])
        runner = Runner(Config.parse({"keywords": ["one", "two"]}), c, AsyncMock())
        with self.assertRaises(RunFailed):
            await runner.run()
        self.assertEqual(c.request_count, 1)
        self.assertEqual(client.post.await_count, 1)
        self.assertEqual(runner.summary["inputs"][1]["status"], "not_started")

    async def test_repeated_page_stops(self):
        c, _ = collector([result([product()], total=99), result([product()], page=2, total=99)])
        async with aclosing(c.pages({"kind": "keyword", "value": "test"}, 5)) as pages:
            await anext(pages)
            with self.assertRaises(ProviderError) as raised:
                await anext(pages)
        self.assertEqual(raised.exception.code, "provider_repeated_page")

    async def test_bad_response_and_page_metadata_stop(self):
        for raw in [{"data": {"items": []}}, result([], total=100),
                    result([product()], page=9), {"items": [], "paginate": {"total": "0", "current": 1, "size": 20}}]:
            c, _ = collector([raw])
            with self.subTest(raw=raw), self.assertRaises(ProviderError):
                _ = [batch async for batch in c.pages({"kind": "keyword", "value": "test"}, 1)]

    async def test_result_allowance_zero_does_not_spend(self):
        c, client = collector([], allowance=0)
        with self.assertRaises(ProviderError):
            _ = [batch async for batch in c.pages({"kind": "keyword", "value": "test"}, 1)]
        client.post.assert_not_awaited()

    async def test_global_result_allowance_caps_returned_products(self):
        c, client = collector([result([product(), product("999999999999")])], allowance=1)
        batches = [batch async for batch in c.pages({"kind": "keyword", "value": "test"}, 1)]
        self.assertEqual(len(batches[0]["products"]), 1)
        with self.assertRaises(ProviderError):
            _ = [batch async for batch in c.pages({"kind": "offer_ids", "value": "999999999999"}, 1)]
        self.assertEqual(client.post.await_count, 1)

    async def test_runner_still_deduplicates_and_resets_per_keyword_limits(self):
        c, _ = collector([result([product()]), result([product()])])
        runner = Runner(Config.parse({"keywords": ["one", "two"], "maxResults": 1}), c, AsyncMock())
        await runner.run()
        self.assertEqual(len(runner.products), 1)
        self.assertEqual(len(next(iter(runner.products.values()))["matched_inputs"]), 2)

    async def test_explicit_api_backend_does_not_start_browser_or_proxy(self):
        pricing = SimpleNamespace(is_pay_per_event=False)
        charging = Mock()
        charging.get_pricing_info.return_value = pricing
        with patch("src.main.Actor.get_charging_manager", return_value=charging), patch("src.main.async_playwright") as browser, patch("src.main.browser_proxy", new=AsyncMock()) as proxy:
            async with collection_backend(Config.parse({}), AsyncMock(), Mock(), owner_env()) as c:
                self.assertIsInstance(c, ElimCollector)
                self.assertEqual(c.request_count, 0)
            browser.assert_not_called()
            proxy.assert_not_awaited()

    async def test_unapproved_backend_cannot_connect_or_fallback(self):
        with patch("src.main.async_playwright") as browser, patch("src.elim.ElimClient.post", new=AsyncMock()) as post:
            with self.assertRaises(InputError):
                async with collection_backend(Config.parse({}), AsyncMock(), Mock(), {"PRODUCT_DATA_SOURCE": "elim"}):
                    self.fail("Unapproved backend started")
            browser.assert_not_called()
            post.assert_not_awaited()

    async def test_ppe_requires_result_event_and_passes_spending_allowance(self):
        charging = Mock()
        pricing = SimpleNamespace(is_pay_per_event=True, per_event_prices={})
        charging.get_pricing_info.return_value = pricing
        with patch("src.main.Actor.get_charging_manager", return_value=charging):
            with self.assertRaises(ProviderError):
                async with collection_backend(Config.parse({}), AsyncMock(), Mock(), owner_env()):
                    self.fail("Missing billing event accepted")
            pricing.per_event_prices = {"apify-default-dataset-item": 0.01}
            charging.calculate_max_event_charge_count_within_limit.return_value = 3
            async with collection_backend(Config.parse({}), AsyncMock(), Mock(), owner_env()) as c:
                self.assertEqual(c.result_allowance, 3)


if __name__ == "__main__":
    unittest.main()
