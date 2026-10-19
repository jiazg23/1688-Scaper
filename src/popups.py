"""Dismiss optional login UI through its own close control, never by DOM removal."""

import logging
import re
from urllib.parse import urlsplit

from playwright.async_api import TimeoutError as BrowserTimeout

from .parser import CARD, KEYWORD, AccessBlocked

LOGIN_HOSTS = {"login.taobao.com", "login.1688.com", "passport.1688.com"}
LOGIN_FRAME = "iframe#alibaba-login-box"
PUBLIC_CONTENT = CARD + ", " + KEYWORD + ", #productTitle h1"
CLOSE_NAME = re.compile(r"^(?:close(?: dialog)?|dismiss|cancel|not now|关闭|关闭窗口|取消|暂不登录|以后再说|[x×✕✖])$", re.I)
CHALLENGE_TEXT = re.compile(r"captcha|安全验证|滑块验证|拖动滑块|slide.{0,20}verify|security verification", re.I)
_log = logging.getLogger(__name__)


def is_login_url(url):
    return (urlsplit(url).hostname or "").lower() in LOGIN_HOSTS


async def public_content_visible(page):
    for locator in await page.locator(PUBLIC_CONTENT).all():
        if await locator.is_visible():
            return True
    return False


async def _close_control(container):
    buttons = container.get_by_role("button", name=CLOSE_NAME)
    for button in await buttons.all():
        if await button.is_visible() and await button.is_enabled():
            return button
    # Only within a recognized login popup, never the whole document. Some X
    # controls are labelled spans rather than semantic buttons.
    labelled = container.locator('[aria-label="close" i], [aria-label="关闭"], [title="close" i], [title="关闭"], img[alt="关闭"], img[alt="close" i]')
    for button in await labelled.all():
        if await button.is_visible():
            return button
    for button in await container.get_by_text(re.compile(r"^[×✕✖x]$", re.I)).all():
        if await button.is_visible():
            return button
    return None


async def dismiss_optional_login(page):
    """One normal close click, only if public 1688 controls exist behind the UI.

    A top-level sign-in URL is not an optional embedded popup. Challenge checking
    must be performed by guard_page before invoking this helper.
    """
    if is_login_url(page.url) or not await public_content_visible(page):
        return False
    targets = []
    for iframe in await page.locator(LOGIN_FRAME).all():
        if not await iframe.is_visible():
            continue
        # The owner supplied this exact frame ID; its X may live outside it.
        # Inspect at most three ancestor containers, never BODY/HTML.
        parent = iframe
        for _ in range(3):
            parent = parent.locator("xpath=..")
            if await parent.evaluate("e => ['BODY','HTML'].includes(e.tagName)"):
                break
            targets.append((parent, iframe))
    for dialog in await page.get_by_role("dialog").all():
        if not await dialog.is_visible():
            continue
        value = await dialog.inner_text()
        if (re.search(r"log\s*in|sign\s*in|登录|登入", value, re.I)
                or await dialog.locator(LOGIN_FRAME).count()):
            targets.append((dialog, dialog))
    for container, popup in targets:
        # Do not dismiss a security verification screen as if it were a login nag.
        if CHALLENGE_TEXT.search(await container.inner_text()):
            continue
        button = await _close_control(container)
        if button is None:
            continue
        await button.click(timeout=5000)
        try:
            await popup.wait_for(state="hidden", timeout=5000)
        except BrowserTimeout:
            raise AccessBlocked("The login popup's close control did not dismiss it.", "login_popup_not_dismissed") from None
        if not await public_content_visible(page):
            raise AccessBlocked("Closing the login popup did not expose usable public content.", "login_popup_no_public_content")
        _log.info("Closed an optional login popup using its normal close control.")
        return True
    return False
