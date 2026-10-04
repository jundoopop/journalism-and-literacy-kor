import socket
from unittest.mock import Mock
import pytest
import url_safety as safety


@pytest.mark.parametrize("url", [
    None, 42, "", "http://www.hani.co.kr/a", "https://127.0.0.1/",
    "https://hani.co.kr.evil.example/a", "https://fakehani.co.kr/a",
    "https://user:pass@www.hani.co.kr/a", "https://www.hani.co.kr:8443/a",
    "https://www.hani.co.kr/\n", "file:///etc/passwd",
])
def test_rejects_untrusted_urls(url):
    with pytest.raises(safety.UnsafeURL):
        safety.validate_news_url(url)


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1"])
def test_rejects_private_dns_answers(monkeypatch, address):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", (address, 443))])
    with pytest.raises(safety.UnsafeURL):
        safety.public_address("www.hani.co.kr")


def fake_response(status=200, headers=None, chunks=None):
    response = Mock(status=status, headers=headers or {"Content-Type": "text/html"})
    response.read.side_effect = chunks or [b"<html>news</html>", b""]
    return response


def test_pins_ip_but_verifies_news_hostname(monkeypatch):
    monkeypatch.setattr(safety, "public_address", lambda host: "93.184.216.34")
    response = fake_response()
    pool = Mock()
    pool.urlopen.return_value = response
    factory = Mock(return_value=pool)
    monkeypatch.setattr(safety.urllib3, "HTTPSConnectionPool", factory)
    assert safety.fetch_news_html("https://www.hani.co.kr/a") == "<html>news</html>"
    assert factory.call_args.args == ("93.184.216.34",)
    assert factory.call_args.kwargs["assert_hostname"] == "www.hani.co.kr"
    assert pool.urlopen.call_args.kwargs["redirect"] is False
    response.close.assert_called_once()
    pool.close.assert_called_once()


def test_redirect_is_validated_before_second_connection(monkeypatch):
    monkeypatch.setattr(safety, "public_address", lambda host: "93.184.216.34")
    pool = Mock()
    pool.urlopen.return_value = fake_response(302, {"Location": "https://127.0.0.1/private"})
    factory = Mock(return_value=pool)
    monkeypatch.setattr(safety.urllib3, "HTTPSConnectionPool", factory)
    with pytest.raises(safety.UnsafeURL):
        safety.fetch_news_html("https://www.hani.co.kr/a")
    assert factory.call_count == 1


def test_bounds_decompressed_response_size(monkeypatch):
    monkeypatch.setattr(safety, "public_address", lambda host: "93.184.216.34")
    monkeypatch.setattr(safety, "MAX_BYTES", 4)
    pool = Mock()
    pool.urlopen.return_value = fake_response(chunks=[b"12345", b""])
    monkeypatch.setattr(safety.urllib3, "HTTPSConnectionPool", Mock(return_value=pool))
    with pytest.raises(ValueError, match="maximum download size"):
        safety.fetch_news_html("https://www.hani.co.kr/a")
    pool.close.assert_called_once()


def test_deadline_expired_during_dns_stops_before_connecting(monkeypatch):
    clock = iter([10.0, 41.0])
    monkeypatch.setattr(safety.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(safety, "public_address", lambda host: "93.184.216.34")
    pool_factory = Mock()
    monkeypatch.setattr(safety.urllib3, "HTTPSConnectionPool", pool_factory)

    with pytest.raises(TimeoutError, match="deadline"):
        safety.fetch_news_html("https://www.hani.co.kr/a")

    pool_factory.assert_not_called()
