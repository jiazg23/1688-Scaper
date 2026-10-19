import json
import unittest
from unittest.mock import AsyncMock

from src.diagnostics import capture_failure, failure_report
from src.parser import AccessBlocked, check_access, check_http_status


class AccessDetectionTests(unittest.TestCase):
    def test_script_reference_is_not_a_verification_page(self):
        html = '<title>1688 products</title><textarea class="cgf-search-input__input"></textarea><script>const url="/_____tmd_____/punish";</script>'
        check_access(html, "https://www.1688.com/")

    def test_hidden_password_field_is_not_a_login_wall(self):
        check_access('<title>1688</title><div style="display:none"><input type=password></div>')

    def test_hidden_challenge_markup_is_not_active(self):
        check_access('<div id="nc_1_wrapper" hidden></div>')

    def test_actual_verification_url_still_stops(self):
        with self.assertRaises(AccessBlocked) as raised:
            check_access('<title>1688</title>', "https://detail.1688.com/offer/123456.html/_____tmd_____/punish?token=SECRET")
        self.assertEqual(raised.exception.code, "verification_url")
        self.assertNotIn("SECRET", str(raised.exception))
        for status in (401, 403, 429):
            with self.subTest(status=status), self.assertRaises(AccessBlocked):
                check_http_status(status)

    def test_active_challenge_control_still_stops(self):
        with self.assertRaises(AccessBlocked) as raised:
            check_access('<div id="nc_1_wrapper">Verify</div>')
        self.assertEqual(raised.exception.code, "verification_element")

    def test_visible_login_form_still_stops(self):
        with self.assertRaises(AccessBlocked) as raised:
            check_access('<form><input type=password></form>')
        self.assertEqual(raised.exception.code, "login_form")

    def test_meta_redirect_still_stops(self):
        with self.assertRaises(AccessBlocked) as raised:
            check_access('<meta http-equiv="refresh" content="0;url=/_____tmd_____/punish">')
        self.assertEqual(raised.exception.code, "verification_redirect")

    def test_standalone_challenge_configuration_still_stops(self):
        with self.assertRaises(AccessBlocked) as raised:
            check_access('<script>window._config_ = {"action":"captcha"};</script>')
        self.assertEqual(raised.exception.code, "verification_config")

    def test_generic_captcha_config_in_app_not_active(self):
        check_access('<textarea class="cgf-search-input__input"></textarea><script>var helper={"action":"captcha"};</script>')

    def test_report_does_not_copy_tokens_or_page_source(self):
        html = '<title>安全验证</title><script>cookie="SECRET"</script><input type=password value="SECRET">'
        error = AccessBlocked("Verification", "verification_title")
        report = failure_report(html, "https://detail.1688.com/_____tmd_____/punish?secret=SECRET", "opening_homepage", error, 403)
        self.assertEqual(report["stage"], "opening_homepage")
        self.assertEqual(report["error_code"], "verification_title")
        self.assertEqual(report["http_status"], 403)
        self.assertTrue(report["verification_url"])
        self.assertNotIn("SECRET", json.dumps(report))


class CaptureFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_saved_report_is_linked_to_exception(self):
        page = AsyncMock()
        page.url = "https://www.1688.com/"
        page.content.return_value = '<title>1688</title>'
        callback = AsyncMock()
        error = AccessBlocked("Verification")
        await capture_failure(page, {"index": 1, "kind": "keyword"}, "opening_homepage", error, callback)
        self.assertEqual(error.diagnostic_key, "FAILURE_01.json")
        self.assertEqual(error.stage, "opening_homepage")
        self.assertEqual(callback.call_args.args[1]["search_mode"], "keyword")

    async def test_storage_failure_does_not_hide_original_error(self):
        page = AsyncMock()
        page.url = "https://www.1688.com/"
        page.content.return_value = "<title>1688</title>"
        error = AccessBlocked("Original verification error")
        await capture_failure(page, {"index": 1, "kind": "keyword"}, "opening_homepage", error, AsyncMock(side_effect=RuntimeError("storage unavailable")))
        self.assertEqual(str(error), "Original verification error")
        self.assertTrue(error.diagnostic_storage_failed)
