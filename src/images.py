"""Bounded HTTPS image downloads with DNS-pinned public destinations.

No browser cookies, private-network targets, environment proxies, or challenge solving.
"""

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 10 * 1024 * 1024


def resolve_public(host, resolver=socket.getaddrinfo):
    addresses = resolver(host, 443, type=socket.SOCK_STREAM)
    ips = list(dict.fromkeys(info[4][0] for info in addresses))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError("Image address is not a public Internet destination.")
    return ips


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip):
        super().__init__(host, timeout=30, context=ssl.create_default_context())
        self.ip = ip

    def connect(self):
        sock = socket.create_connection((self.ip, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


def image_type(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError("Expected a PNG, JPEG, or WebP image, not HTML, SVG, or a website URL.")


def download_image(url):
    """Resolve and pin every redirect destination before sending the request."""
    for _ in range(5):
        p = urlsplit(url)
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in {None, 443}:
            raise ValueError("Image URL must use public HTTPS on the standard port.")
        ips = resolve_public(p.hostname)
        connection = PinnedHTTPS(p.hostname, ips[0])
        try:
            target = p.path or "/"
            if p.query:
                target += "?" + p.query
            connection.request("GET", target, headers={"Accept": "image/png,image/jpeg,image/webp", "User-Agent": "1688-sourcing-actor/0.1"})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Image source sent a redirect without a destination.")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError(f"Image source returned HTTP {response.status}.")
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("Image exceeds the 10 MB limit.")
            return data, image_type(data)
        finally:
            connection.close()
    raise ValueError("Image source redirected too many times.")
