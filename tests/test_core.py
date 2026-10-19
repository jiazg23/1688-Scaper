import copy
import csv
import io
import json
from pathlib import Path
import socket
import unittest

from jsonschema import Draft7Validator, validate

from src.config import Config, InputError, product_url
from src.exports import csv_text, supplier_rows
from src.images import image_type, resolve_public
from src.parser import parse_search, parse_product, AccessBlocked, UnsupportedLayout
from src.pricing import quote, decimal_text
from src.runner import Runner, RunFailed

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
HTML = (FIXTURES / "currency-usd.html").read_text() + (FIXTURES / "search-results.html").read_text()
PAGINATION = (FIXTURES / "pagination.html").read_text()


class InputTests(unittest.TestCase):
    def test_default_and_schema_agree(self):
        schema = json.loads((ROOT / ".actor/INPUT_SCHEMA.json").read_text())
        defaults = {k: v["default"] for k, v in schema["properties"].items() if "default" in v}
        validate(defaults, schema)
        self.assertEqual(Config.parse({}), Config.parse(defaults))
        self.assertTrue(Config.parse({}).save_csv)
        self.assertTrue(Config.parse({}).use_proxy)

    def test_urls_normalized(self):
        self.assertEqual(product_url("1071313125369"), "https://detail.1688.com/offer/1071313125369.html")
        self.assertEqual(product_url("https://m.1688.com/offer/1071313125369.html?tracking=1"), product_url("1071313125369"))

    def test_reject_bad_urls(self):
        for url in ["https://1688.com.evil.test/offer/123456.html", "https://localhost/offer/123456.html", "http://detail.1688.com/offer/123456.html", "https://u:p@detail.1688.com/offer/123456.html", "https://www.1688.com", "https://detail.1688.com:444/offer/123456.html", "https://[oops"]:
            with self.subTest(url=url), self.assertRaises(InputError):
                product_url(url)

    def test_no_silent_blank_input_or_wrong_mode(self):
        for raw in [{"searchTerms": []}, {"searchMode": "urls"}, {"searchMode": "image"}, {"searchMode": "supplier"}]:
            with self.subTest(raw=raw), self.assertRaises(InputError):
                Config.parse(raw)

    def test_reject_bool_and_string_numbers(self):
        for raw in [{"orderQuantity": True}, {"maxPagesText": "5"}, {"saveCsvFile": "false"}, {"maxPagesText": 0}]:
            with self.subTest(raw=raw), self.assertRaises(InputError):
                Config.parse(raw)

    def test_keywords_dedup(self):
        self.assertEqual(Config.parse({"searchTerms": [" hair dryer ", "hair dryer"]}).terms, ["hair dryer"])

    def test_images_not_pages_or_blob(self):
        for value in ["blob:https://www.1688.com/1234", "http://images.test/product.jpg", "https://user:pass@images.test/a.jpg"]:
            with self.assertRaises(InputError):
                Config.parse({"searchMode": "image", "imageUrls": [value]})

    def test_filename_safety(self):
        for name in ["../foo.csv", "foo.json", "folder/a.csv", "a.csv\n", "1688_suppliers.csv"]:
            with self.assertRaises(InputError):
                Config.parse({"csvFilename": name})


class ParserTests(unittest.TestCase):
    def test_all_sixty_real_saved_cards(self):
        result = parse_search(HTML + PAGINATION)
        self.assertEqual(len(result["products"]), 60)
        self.assertTrue(result["has_next"])
        self.assertEqual(result["page_number"], 1)
        first = result["products"][0]
        self.assertEqual(first["product_id"], "1071313125369")
        self.assertEqual(first["display_price"], "3.84")
        self.assertEqual(first["currency"], "USD")
        self.assertEqual(first["moq"], 2)
        self.assertEqual(first["supplier_name"], "Jieyang Jiayi Technology Co., Ltd.")
        self.assertEqual(first["supplier_url"], "https://shop1460998052413.1688.com")
        self.assertIsNone(first["verified_supplier"])
        self.assertIsNone(first["manufacturer"])
        self.assertEqual(first["price_tiers"], [])

    def test_ambiguous_symbol_is_not_assumed_usd_or_cny(self):
        cards = (FIXTURES / "search-results.html").read_text()
        self.assertIsNone(parse_search(cards)["products"][0]["currency"])
        self.assertIsNone(parse_search(HTML.replace("USD", "CNY"))["products"][0]["currency"])

    def test_dropdown_selected_currency(self):
        html = '<div class="currency-section"><div class="select-value"><span class="select-text">USD ($)</span></div></div>'
        self.assertEqual(parse_search(html + (FIXTURES / "search-results.html").read_text())["products"][0]["currency"], "USD")

    def test_hidden_rating_not_exported(self):
        products = parse_search(HTML)["products"]
        self.assertIsNone(products[-1]["supplier_rating"])
        # Stored HTML contains numeric ratings in display:none containers.
        self.assertIsNone(products[1]["supplier_rating"])
        visible = HTML.replace('style="display: none;"', '')
        self.assertEqual(parse_search(visible)["products"][1]["supplier_rating"], 5.0)
        self.assertEqual(products[1]["supplier_years"], 4)

    def test_unknown_layout_is_error_not_empty_success(self):
        with self.assertRaises(UnsupportedLayout):
            parse_search("<main>loading</main>")

    def test_block_and_login_detection(self):
        for html in ['<title>安全验证</title>', '<script>var config={"action":"captcha"}</script>', '<iframe src="/punish"></iframe>']:
            with self.assertRaises(AccessBlocked):
                parse_search(html)
        with self.assertRaises(AccessBlocked):
            parse_search(HTML, "https://detail.1688.com/_____tmd_____/punish")

    def test_missing_pagination_is_unknown(self):
        self.assertIsNone(parse_search(HTML)["has_next"])

    def test_duplicate_card_dedup(self):
        self.assertEqual(len(parse_search(HTML + HTML)["products"]), 60)

    def test_detail_requires_matching_identity(self):
        target = product_url("1071313125369")
        data = {"@type": "Product", "url": target, "name": "Synthetic fixture product", "offers": {"@type": "Offer", "price": "12.50", "priceCurrency": "CNY"}}
        html = '<script type="application/ld+json">' + json.dumps(data) + '</script>'
        result = parse_product(html, target)
        self.assertEqual(result["display_price"], "12.50")
        self.assertEqual(result["currency"], "CNY")
        with self.assertRaises(UnsupportedLayout):
            parse_product(html, product_url("999999999999"))


class PricingTests(unittest.TestCase):
    def setUp(self):
        self.product = {"moq": 10, "currency": "CNY", "quantity_unit": "piece", "price_basis": "quantity_tiers", "price_tiers": [
            {"min_quantity": 10, "max_quantity": 99, "unit_price": "3.84"},
            {"min_quantity": 100, "unit_price": "3.50"}]}

    def test_exact_tier_boundary(self):
        self.assertEqual(quote(self.product, 99)["product_subtotal"], "380.16")
        self.assertEqual(quote(self.product, 100)["applicable_unit_price"], "3.50")
        self.assertEqual(quote(self.product, 100)["product_subtotal"], "350.00")

    def test_below_moq(self):
        result = quote(self.product, 9)
        self.assertEqual(result["quote_status"], "below_moq")
        self.assertIsNone(result["product_subtotal"])

    def test_search_price_not_bulk_quote(self):
        result = quote(parse_search(HTML)["products"][0], 100)
        self.assertEqual(result["quote_status"], "listing_price_only")
        self.assertIsNone(result["product_subtotal"])

    def test_unverified_quantity_and_currency(self):
        for key, value, status in [("currency", None, "currency_unknown"), ("quantity_unit", "kg", "quantity_basis_unknown"), ("price_basis", "variants", "variant_selection_required")]:
            self.assertEqual(quote({**self.product, key: value}, 100)["quote_status"], status)

    def test_invalid_and_overlapping_tiers(self):
        for tiers in [[{"min_quantity": 10, "unit_price": "NaN"}], [{"min_quantity": 10, "unit_price": "1"}, {"min_quantity": 20, "unit_price": "2"}], [{"min_quantity": 10, "max_quantity": 100, "unit_price": "1"}, {"min_quantity": 100, "unit_price": "2"}]]:
            self.assertEqual(quote({**self.product, "price_tiers": tiers}, 100)["quote_status"], "invalid_tiers")

    def test_decimal_rejects_nonfinite_and_negative(self):
        for value in ["NaN", "Infinity", "-1", "", None]:
            self.assertIsNone(decimal_text(value))


class ExportAndSchemaTests(unittest.TestCase):
    def test_csv_formula_safety(self):
        data = csv_text([{"product_id": "123456", "title": "  =HYPERLINK(1)", "marketing_tags": ["tag"]}])
        parsed = next(csv.DictReader(io.StringIO(data.lstrip("\ufeff"))))
        self.assertTrue(parsed["title"].startswith("'"))
        self.assertEqual(json.loads(parsed["marketing_tags"]), ["tag"])

    def test_supplier_shortlist_no_currency_blending(self):
        products = parse_search(HTML)["products"]
        first = products[0]
        second = {**first, "product_id": "999999999999", "currency": "CNY"}
        row = supplier_rows([first, second])[0]
        self.assertEqual(row["product_count"], 2)
        self.assertEqual(row["currencies"], ["USD", "CNY"])

    def test_schemas_and_output_version(self):
        for name in ["INPUT_SCHEMA", "OUTPUT_SCHEMA"]:
            Draft7Validator.check_schema(json.loads((ROOT / f".actor/{name}.json").read_text()))
        output = json.loads((ROOT / ".actor/OUTPUT_SCHEMA.json").read_text())
        self.assertEqual(output["actorOutputSchemaVersion"], 1)
        dataset = json.loads((ROOT / ".actor/DATASET_SCHEMA.json").read_text())
        Draft7Validator.check_schema(dataset["fields"])
        for product in parse_search(HTML)["products"]:
            validate({**product, **quote(product, 100)}, dataset["fields"])

    def test_private_image_addresses_rejected(self):
        for address in ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1"]:
            resolver = lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]
            with self.assertRaises(ValueError):
                resolve_public("image.test", resolver)

    def test_non_image_rejected(self):
        with self.assertRaises(ValueError):
            image_type(b"<html>login</html>")
        self.assertEqual(image_type(b"\x89PNG\r\n\x1a\n"), "image/png")


class FakeCollector:
    def __init__(self, actions):
        self.actions, self.started, self.closed = actions, [], []

    async def pages(self, spec, max_pages):
        index = spec["index"]
        self.started.append(index)
        try:
            for action in self.actions[index - 1]:
                if isinstance(action, Exception):
                    raise action
                yield copy.deepcopy(action)
        finally:
            self.closed.append(index)


class RunnerTests(unittest.IsolatedAsyncioTestCase):
    async def make(self, raw, actions):
        snapshots = []
        async def save(products, summary):
            snapshots.append(copy.deepcopy((products, summary)))
        collector = FakeCollector(actions)
        return Runner(Config.parse(raw), collector, save), collector, snapshots

    def batch(self, products=None, more=True):
        return {"products": products or parse_search(HTML)["products"][:2], "has_next": more, "page_number": 1}

    async def test_per_image_counter_and_global_dedup(self):
        batch = self.batch()
        runner, collector, snapshots = await self.make({"searchMode": "image", "imageUrls": ["https://images.test/1.jpg", "https://images.test/2.jpg"], "maxProductsPerImage": 2}, [[batch], [batch]])
        products = await runner.run()
        self.assertEqual(collector.started, [1, 2])
        self.assertEqual(collector.closed, [1, 2])
        self.assertEqual(len(products), 2)
        self.assertEqual(len(products[0]["matched_inputs"]), 2)
        self.assertEqual([i["products"] for i in runner.summary["inputs"]], [2, 2])
        self.assertTrue(snapshots)

    async def test_partial_pages_preserved(self):
        runner, _, snapshots = await self.make({}, [[self.batch(), UnsupportedLayout("next page changed")]])
        products = await runner.run()
        self.assertEqual(len(products), 2)
        self.assertEqual(runner.summary["status"], "partial")
        self.assertEqual(len(snapshots[-1][0]), 2)

    async def test_access_block_stops_remaining_inputs(self):
        runner, collector, _ = await self.make({"searchTerms": ["first", "second"]}, [[AccessBlocked("verification")], [self.batch(more=False)]])
        with self.assertRaises(RunFailed):
            await runner.run()
        self.assertEqual(collector.started, [1])
        self.assertEqual(runner.summary["inputs"][1]["status"], "not_started")

    async def test_no_results_is_failure(self):
        runner, _, _ = await self.make({}, [[UnsupportedLayout("missing cards")]])
        with self.assertRaises(RunFailed):
            await runner.run()

    async def test_strict_failure_keeps_earlier_rows(self):
        runner, _, _ = await self.make({"failOnNoResults": True}, [[self.batch(), UnsupportedLayout("bad next page")]])
        with self.assertRaises(RunFailed):
            await runner.run()
        self.assertEqual(len(runner.products), 2)


if __name__ == "__main__":
    unittest.main()
