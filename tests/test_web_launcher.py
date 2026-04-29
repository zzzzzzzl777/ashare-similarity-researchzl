from __future__ import annotations

import pytest


def test_choose_available_port_scans_forward_until_it_finds_a_free_port(load_module_or_fail, monkeypatch):
    launcher = load_module_or_fail("ashare_similarity.web_launcher")
    checks: list[tuple[str, int]] = []
    availability = {8011: False, 8012: False, 8013: True}

    def fake_is_port_available(host: str, port: int) -> bool:
        checks.append((host, port))
        return availability.get(port, False)

    monkeypatch.setattr(launcher, "is_port_available", fake_is_port_available)

    selected = launcher.choose_available_port("0.0.0.0", 8011, scan_limit=3)

    assert selected == 8013
    assert checks == [("0.0.0.0", 8011), ("0.0.0.0", 8012), ("0.0.0.0", 8013)]


def test_choose_available_port_raises_when_scan_range_is_exhausted(load_module_or_fail, monkeypatch):
    launcher = load_module_or_fail("ashare_similarity.web_launcher")
    monkeypatch.setattr(launcher, "is_port_available", lambda host, port: False)

    with pytest.raises(RuntimeError, match=r"8200-8202"):
        launcher.choose_available_port("127.0.0.1", 8200, scan_limit=2)


def test_discover_ipv4_addresses_filters_unusable_ips_and_sorts_lan_first(load_module_or_fail, monkeypatch):
    launcher = load_module_or_fail("ashare_similarity.web_launcher")

    def fake_getaddrinfo(hostname, service, family):
        del hostname, service
        assert family == launcher.socket.AF_INET
        return [
            (launcher.socket.AF_INET, None, None, None, ("10.0.0.8", 0)),
            (launcher.socket.AF_INET, None, None, None, ("127.0.0.1", 0)),
            (launcher.socket.AF_INET, None, None, None, ("172.16.0.9", 0)),
            (launcher.socket.AF_INET, None, None, None, ("169.254.1.2", 0)),
        ]

    class _FakeDatagramSocket:
        def connect(self, target):
            assert target == ("8.8.8.8", 80)

        def getsockname(self):
            return ("192.168.1.20", 54321)

        def close(self) -> None:
            return None

    monkeypatch.setattr(launcher.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(launcher.socket, "socket", lambda *args, **kwargs: _FakeDatagramSocket())

    discovered = launcher.discover_ipv4_addresses()

    assert discovered == ["192.168.1.20", "10.0.0.8", "172.16.0.9"]


def test_build_access_urls_for_wildcard_host_lists_lan_addresses_before_loopback(load_module_or_fail, monkeypatch):
    launcher = load_module_or_fail("ashare_similarity.web_launcher")
    monkeypatch.setattr(launcher, "discover_ipv4_addresses", lambda: ["192.168.1.20", "10.0.0.8", "192.168.1.20"])

    urls = launcher.build_access_urls("0.0.0.0", 8011)

    assert urls == [
        "http://192.168.1.20:8011/",
        "http://10.0.0.8:8011/",
        "http://127.0.0.1:8011/",
        "http://localhost:8011/",
    ]


def test_build_launch_info_prefers_localhost_browser_url_for_local_browser_use(load_module_or_fail, monkeypatch):
    launcher = load_module_or_fail("ashare_similarity.web_launcher")

    monkeypatch.setattr(launcher, "choose_available_port", lambda host, preferred_port, scan_limit=0: preferred_port + 2)
    monkeypatch.setattr(launcher, "discover_ipv4_addresses", lambda: ["10.0.0.8"])

    launch = launcher.build_launch_info("0.0.0.0", 8011, scan_limit=5)

    assert launch.host == "0.0.0.0"
    assert launch.port == 8013
    assert launch.browser_url == "http://localhost:8013/"
    assert launch.access_urls == [
        "http://10.0.0.8:8013/",
        "http://127.0.0.1:8013/",
        "http://localhost:8013/",
    ]
