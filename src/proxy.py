"""One explicit residential proxy country/session per run; no denial fallback."""

from urllib.parse import unquote, urlsplit
from uuid import uuid4

from apify import Actor


async def browser_proxy(config, log=None):
    if not config.use_proxy:
        if log:
            log("Apify Proxy is disabled; using a direct browser connection.")
        return None
    try:
        proxy_config = await Actor.create_proxy_configuration(
            groups=["RESIDENTIAL"], country_code=config.proxy_country)
        if proxy_config is None:
            raise RuntimeError("No proxy configuration returned")
        # Create once before browsing. Do not switch country or session after
        # a login/verification response. Never log the authenticated proxy URL.
        url = await proxy_config.new_url(session_id=uuid4().hex)
        parts = urlsplit(url or "")
        if parts.scheme not in {"http", "https"} or not parts.hostname or not parts.port:
            raise ValueError("Invalid proxy URL")
        result = {"server": f"{parts.scheme}://{parts.hostname}:{parts.port}",
                  "username": unquote(parts.username or ""),
                  "password": unquote(parts.password or "")}
    except Exception:
        # SDK/provider exceptions can contain authenticated connection details.
        raise RuntimeError(
            f"Unable to initialize Apify residential proxies for {config.proxy_country}. "
            "Check Proxy access, available country coverage and billing in Apify Console. "
            "No automatic country or direct-connection fallback was attempted.") from None
    if log:
        log(f"Apify residential proxy configured: country={config.proxy_country}. "
            "Traffic is billed through Apify; country availability and site access are not guaranteed.")
    return result
