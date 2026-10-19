"""Proxy configuration tests use mocks only: no provider or site requests."""

import unittest
from unittest.mock import AsyncMock, patch

from src.config import Config
from src.proxy import browser_proxy


class ResidentialProxyTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_proxy_does_not_initialize_paid_access(self):
        with patch("src.proxy.Actor.create_proxy_configuration", new_callable=AsyncMock) as create:
            self.assertIsNone(await browser_proxy(Config.parse({"useApifyProxy": False})))
            create.assert_not_awaited()

    async def test_residential_group_and_explicit_country_are_used(self):
        for country in ["CN", "HK"]:
            with self.subTest(country=country):
                provider = AsyncMock()
                provider.new_url.return_value = "http://user:password@proxy.test:8000"
                with patch("src.proxy.Actor.create_proxy_configuration", new=AsyncMock(return_value=provider)) as create:
                    result = await browser_proxy(Config.parse({"proxyCountryMode": country}))
                create.assert_awaited_once_with(groups=["RESIDENTIAL"], country_code=country)
                provider.new_url.assert_awaited_once()
                session = provider.new_url.call_args.kwargs["session_id"]
                self.assertRegex(session, r"^[a-f0-9]{32}$")
                self.assertEqual(result["server"], "http://proxy.test:8000")

    async def test_credentials_are_decoded_but_not_logged(self):
        provider = AsyncMock()
        provider.new_url.return_value = "http://user%2Bname:SECRET%40password@proxy.test:8000"
        logs = []
        with patch("src.proxy.Actor.create_proxy_configuration", new=AsyncMock(return_value=provider)):
            result = await browser_proxy(Config.parse({}), logs.append)
        self.assertEqual(result["username"], "user+name")
        self.assertEqual(result["password"], "SECRET@password")
        self.assertNotIn("SECRET", " ".join(logs))
        self.assertNotIn("proxy.test", " ".join(logs))
        self.assertIn("billed through Apify", " ".join(logs))

    async def test_provider_error_is_sanitized_and_never_falls_back(self):
        with patch("src.proxy.Actor.create_proxy_configuration", new=AsyncMock(side_effect=RuntimeError("SECRET connection"))) as create:
            with self.assertRaises(RuntimeError) as raised:
                await browser_proxy(Config.parse({}))
        self.assertNotIn("SECRET", str(raised.exception))
        self.assertIn("No automatic", str(raised.exception))
        create.assert_awaited_once_with(groups=["RESIDENTIAL"], country_code="CN")

    async def test_missing_proxy_access_is_explicit_error(self):
        with patch("src.proxy.Actor.create_proxy_configuration", new=AsyncMock(return_value=None)):
            with self.assertRaisesRegex(RuntimeError, "Check Proxy access"):
                await browser_proxy(Config.parse({}))

    async def test_no_second_session_on_connection_failure(self):
        provider = AsyncMock()
        provider.new_url.side_effect = RuntimeError("SECRET unavailable country")
        with patch("src.proxy.Actor.create_proxy_configuration", new=AsyncMock(return_value=provider)):
            with self.assertRaises(RuntimeError):
                await browser_proxy(Config.parse({}))
        provider.new_url.assert_awaited_once()

    async def test_malformed_proxy_url_is_sanitized(self):
        for url in [None, "http://SECRET@proxy.test", "socks5://SECRET@proxy.test:1080"]:
            provider = AsyncMock()
            provider.new_url.return_value = url
            with self.subTest(url=url), patch("src.proxy.Actor.create_proxy_configuration", new=AsyncMock(return_value=provider)):
                with self.assertRaises(RuntimeError) as raised:
                    await browser_proxy(Config.parse({}))
                self.assertNotIn("SECRET", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
