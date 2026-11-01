"""Bounded HTTPS fetching for the supported news sites.

Validate every redirect and pin TLS connections to a validated public address.
This prevents a second DNS lookup from turning a validated host into a private IP.
"""
import ipaddress
import re
import socket
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

import certifi
import urllib3

NEWS_DOMAINS = ("chosun.com", "joongang.co.kr", "hani.co.kr", "hankookilbo.com", "khan.co.kr")
MAX_BYTES = 4 * 1024 * 1024
MAX_REDIRECTS = 3


class UnsafeURL(ValueError):
    pass


def validate_news_url(url):
    if not isinstance(url, str) or not url or len(url) > 4096:
        raise UnsafeURL("A news HTTPS URL of at most 4096 characters is required")
    if any(ord(c) <= 32 for c in url) or "\\" in url:
        raise UnsafeURL("URL contains invalid characters")
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        valid_host = any(host == d or host.endswith("." + d) for d in NEWS_DOMAINS)
        if (parsed.scheme != "https" or not valid_host or parsed.port not in (None, 443)
                or parsed.username is not None or parsed.password is not None):
            raise UnsafeURL("Only HTTPS URLs on supported news domains are allowed")
    except ValueError as exc:
        raise UnsafeURL(str(exc)) from exc
    return urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))


def public_address(host):
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    ips = list(dict.fromkeys(item[4][0] for item in addresses))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise UnsafeURL("News host resolved to a non-public address")
    return ips[0]


def fetch_news_html(url):
    deadline = time.monotonic() + 30
    for hop in range(MAX_REDIRECTS + 1):
        url = validate_news_url(url)
        parsed = urlsplit(url)
        address = public_address(parsed.hostname)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Article download deadline exceeded")
        # TLS still verifies the original news hostname, never the pinned IP.
        pool = urllib3.HTTPSConnectionPool(
            address, port=443, server_hostname=parsed.hostname,
            assert_hostname=parsed.hostname, cert_reqs="CERT_REQUIRED",
            ca_certs=certifi.where(),
        )
        response = None
        try:
            response = pool.urlopen(
                "GET", urlunsplit(("", "", parsed.path or "/", parsed.query, "")),
                headers={"Host": parsed.hostname, "User-Agent": "NewsLiteracy/1.0"},
                timeout=urllib3.Timeout(connect=min(3, remaining), read=min(10, remaining)),
                retries=False, redirect=False, preload_content=False,
            )
            if response.status in (301, 302, 303, 307, 308):
                if hop == MAX_REDIRECTS or not response.headers.get("Location"):
                    raise UnsafeURL("Invalid or excessive redirects")
                url = urljoin(url, response.headers["Location"])
                continue
            if response.status != 200:
                raise ValueError(f"News server returned HTTP {response.status}")
            content_type = response.headers.get("Content-Type", "").lower()
            if not content_type.startswith(("text/html", "application/xhtml+xml")):
                raise ValueError("Expected an HTML article")
            chunks, size = [], 0
            while True:
                chunk = response.read(65536, decode_content=True)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("Article exceeds maximum download size")
                if time.monotonic() > deadline:
                    raise TimeoutError("Article download deadline exceeded")
                chunks.append(chunk)
            charset = re.search(r"charset=([^;\s]+)", content_type)
            encoding = charset.group(1).strip('"\'') if charset else "utf-8"
            return b"".join(chunks).decode(encoding, errors="replace")
        finally:
            if response is not None:
                response.close()
            pool.close()
