"""Opt-in, documented Elim API adapter. No browser/proxy or private-site fallback.

Contract sources: https://elim.asia/en/docs/product/ and /en/docs/auth/.
Only offline synthetic responses have been tested. Provider permission is not
implied by this module or by possessing an API key.
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

from .config import InputError, product_url
from .parser import CollectionError, supplier_url
from .pricing import decimal_text

BASE_URL = "https://openapi.elim.asia"
MAX_BODY_BYTES = 2 * 1024 * 1024


class ProviderError(CollectionError):
    terminal = True

    def __init__(self, message, code="provider_error"):
        super().__init__(message)
        self.code = code


def data_source(environ):
    source = environ.get("PRODUCT_DATA_SOURCE", "browser")
    if source not in {"browser", "elim"}:
        raise InputError("PRODUCT_DATA_SOURCE must be browser or elim. No automatic fallback is supported.")
    return source


@dataclass(frozen=True)
class ElimSettings:
    api_key: str = field(repr=False)
    max_requests: int = 5

    @classmethod
    def from_env(cls, environ):
        if environ.get("ELIM_COMMERCIAL_USE_APPROVED") != "true":
            raise InputError("Elim is disabled: obtain written permission covering the paid Apify Actor and customer exports before owner activation.")
        key = environ.get("ELIM_API_KEY", "")
        if not key or key != key.strip() or len(key) > 2048 or any(ord(c) < 33 or ord(c) > 126 for c in key):
            raise InputError("Set a valid ELIM_API_KEY in the Actor's secret environment settings, not its public input.")
        limit = environ.get("ELIM_MAX_REQUESTS_PER_RUN", "5")
        if not re.fullmatch(r"[0-9]{1,3}", limit) or not 1 <= int(limit) <= 100:
            raise InputError("ELIM_MAX_REQUESTS_PER_RUN must be between 1 and 100; default is five attempts across the whole run.")
        at_home = environ.get("APIFY_IS_AT_HOME", "").lower() in {"1", "true"}
        paying = environ.get("APIFY_USER_IS_PAYING", "").lower() in {"1", "true"}
        if at_home and not paying and environ.get("ELIM_ALLOW_UNPAID_RUNS") != "true":
            raise InputError("Provider calls for unpaid or unknown-plan users are disabled. Owner-funded previews require explicit ELIM_ALLOW_UNPAID_RUNS=true and still use the request cap.")
        return cls(key, int(limit))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never send the key to a redirect destination.


class ElimClient:
    def __init__(self, settings):
        self.settings = settings

    async def post(self, path, payload):
        return await asyncio.to_thread(self._post, path, payload)

    def _post(self, path, payload):
        if path not in {"/v2/products/search", "/v2/products/find"}:
            raise ProviderError("Unsupported provider endpoint.", "provider_endpoint")
        request = Request(BASE_URL + path, data=json.dumps(payload).encode(), method="POST",
                          headers={"Content-Type": "application/json", "Accept": "application/json",
                                   "x-api-key": self.settings.api_key})
        # Standard HTTPS API access only. Do not inherit a target-site proxy.
        opener = build_opener(ProxyHandler({}), NoRedirect())
        try:
            with opener.open(request, timeout=30) as response:
                content_type = response.headers.get_content_type()
                if response.status != 200 or content_type != "application/json":
                    raise ProviderError("Provider did not return HTTP 200 JSON; no fallback or retry attempted.", "provider_response")
                body = response.read(MAX_BODY_BYTES + 1)
        except HTTPError as error:
            status = error.code
            error.close()
            raise ProviderError(f"Provider returned HTTP {status}; check account permissions, quota or rate limits. No retry attempted.", f"provider_http_{status}") from None
        except (URLError, TimeoutError, OSError):
            raise ProviderError("Provider request failed or timed out; no automatic retry attempted.", "provider_transport") from None
        if len(body) > MAX_BODY_BYTES:
            raise ProviderError("Provider response exceeded the size limit.", "provider_size")
        try:
            result = json.loads(body)
        except (ValueError, UnicodeError):
            raise ProviderError("Provider returned invalid JSON.", "provider_json") from None
        if not isinstance(result, dict):
            raise ProviderError("Provider response must be a JSON object.", "provider_schema")
        return result


def safe_text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def normalize_product(raw, expected_id=None):
    if not isinstance(raw, dict):
        raise ProviderError("Provider product is not an object.", "provider_schema")
    identity = raw.get("id")
    offer_id = str(identity) if type(identity) in {str, int} else ""
    title = safe_text(raw.get("title"))
    if not re.fullmatch(r"[0-9]{6,20}", offer_id) or not title:
        raise ProviderError("Provider product is missing a valid numeric ID or original title.", "provider_schema")
    if expected_id is not None and offer_id != expected_id:
        raise ProviderError("Provider returned a different Offer ID; product was rejected.", "provider_identity")
    # The provider's API prices can differ from website prices. Do not infer
    # currency, SKU ladders, verified status or a firm quotation from generic fields.
    moq_value = raw.get("moq")
    moq = (int(str(moq_value)) if type(moq_value) in {int, str}
           and re.fullmatch(r"[0-9]{1,10}", str(moq_value)) and int(moq_value) > 0 else None)
    images = []
    for value in raw.get("img_urls", []) if isinstance(raw.get("img_urls"), list) else []:
        if not isinstance(value, str):
            continue
        try:
            parts = urlsplit(value)
            if parts.scheme == "https" and parts.hostname and not parts.username and not parts.password:
                images.append(value)
        except ValueError:
            continue
    seller_type = raw.get("seller_type")
    return {"product_id": offer_id, "title": title, "product_url": product_url(offer_id),
            "image_url": images[0] if images else None, "image_urls": list(dict.fromkeys(images)),
            "display_price": decimal_text(raw.get("price")), "currency": None,
            "price_symbol": None, "currency_source": None,
            "price_basis": "provider_api_price", "price_tiers": [],
            "price_context": "Provider API price; may differ from 1688 website prices. Currency and quantity-tier mapping are not validated.",
            "moq": moq, "moq_text": str(moq) if moq else None,
            "quantity_unit": safe_text(raw.get("unit")),
            "supplier_id": str(raw["shop_id"]) if type(raw.get("shop_id")) in {str, int} else None,
            "supplier_name": safe_text(raw.get("shop_name")),
            "supplier_url": supplier_url(raw.get("seller_shop_url", "")),
            "supplier_years": None, "supplier_rating": None, "sales_text": None,
            "marketing_tags": [], "is_sponsored": None, "verified_supplier": None, "manufacturer": None,
            "provider_seller_type": seller_type if isinstance(seller_type, str) and seller_type in {"seller", "merchant", "factory"} else None,
            "extraction_source": "elim_documented_api", "detail_completeness": "provider_subset_unvalidated"}


class ElimCollector:
    def __init__(self, settings, max_products, *, client=None, log=None,
                 result_allowance=None, clock=time.monotonic, sleep=asyncio.sleep):
        self.client = client if client is not None else ElimClient(settings)
        self.max_requests, self.max_products = settings.max_requests, max_products
        self.log, self.result_allowance = log, result_allowance
        self.clock, self.sleep = clock, sleep
        self.request_count, self.last_request = 0, None
        self.emitted_ids = set()

    @property
    def metrics(self):
        return {"data_source": "elim", "provider_requests_attempted": self.request_count,
                "provider_request_limit": self.max_requests,
                "provider_live_validated": False}

    async def request(self, path, payload):
        if self.request_count >= self.max_requests:
            raise ProviderError("Owner's whole-run provider request cap reached; earlier products are retained.", "provider_request_limit")
        if self.result_allowance is not None and len(self.emitted_ids) >= self.result_allowance:
            raise ProviderError("Apify result spending allowance reached; no further provider requests made.", "provider_result_limit")
        if self.last_request is not None:
            await self.sleep(max(0, 2.1 - (self.clock() - self.last_request)))
        self.request_count += 1  # Count every attempted call, including failures.
        self.last_request = self.clock()
        if self.log:
            self.log(f"Elim API request {self.request_count}/{self.max_requests}; provider billing is separate from Apify.")
        return await self.client.post(path, payload)

    def reserve(self, products):
        accepted = []
        for product in products:
            identity = product["product_id"]
            if identity not in self.emitted_ids:
                if self.result_allowance is not None and len(self.emitted_ids) >= self.result_allowance:
                    break
                self.emitted_ids.add(identity)
            accepted.append(product)
        return accepted

    async def pages(self, spec, max_pages):
        if spec["kind"] == "offer_ids":
            raw = await self.request("/v2/products/find", {"platform": "alibaba", "id": spec["value"]})
            products = self.reserve([normalize_product(raw, expected_id=spec["value"])])
            yield {"products": products, "has_next": False, "page_number": 1}
            return
        if spec["kind"] != "keyword":
            raise ProviderError("Provider supports only keywords and numeric Offer IDs.", "provider_mode")
        signatures, seen = set(), set()
        size = min(40, max(20, self.max_products))
        for page in range(1, max_pages + 1):
            raw = await self.request("/v2/products/search", {"platform": "alibaba", "q": spec["value"],
                                                           "page": page, "size": size})
            items = raw.get("items")
            if not isinstance(items, list) or len(items) > 40:
                raise ProviderError("Unsupported provider search response; expected a documented items list of at most 40 products.", "provider_schema")
            products = [normalize_product(item) for item in items]
            signature = tuple(sorted(p["product_id"] for p in products))
            if signature and signature in signatures:
                raise ProviderError("Provider repeated a results page; pagination stopped.", "provider_repeated_page")
            if signature:
                signatures.add(signature)
            metadata = raw.get("paginate")
            if metadata is not None:
                if not isinstance(metadata, dict) or any(type(metadata.get(k)) is not int for k in ("total", "current", "size")):
                    raise ProviderError("Unsupported provider pagination metadata.", "provider_pagination")
                if metadata["current"] != page or not 1 <= metadata["size"] <= 40 or metadata["total"] < 0:
                    raise ProviderError("Provider pagination does not match the requested page.", "provider_pagination")
                offset = (page - 1) * metadata["size"]
                if (len(items) > metadata["size"]
                        or (not items and offset < metadata["total"])
                        or (items and offset + len(items) > metadata["total"])):
                    raise ProviderError("Provider pagination conflicts with returned items.", "provider_pagination")
                has_next = page * metadata["size"] < metadata["total"]
            else:
                # No inferred exhaustion from a short page: metadata is optional.
                has_next = None
            remaining = self.max_products - len(seen)
            products = products[:remaining]
            seen.update(p["product_id"] for p in products)
            products = self.reserve(products)
            yield {"products": products, "has_next": has_next, "page_number": page}
            if has_next is False:
                return
            if has_next is None:
                raise ProviderError("Provider omitted pagination metadata; collected products are partial, not a verified last page.", "provider_pagination_missing")
