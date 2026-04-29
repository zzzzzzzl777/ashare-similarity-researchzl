from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass
import ipaddress
import socket


DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8011
DEFAULT_PORT_SCAN_LIMIT = 20


@dataclass(frozen=True)
class LaunchInfo:
    host: str
    port: int
    browser_url: str
    access_urls: list[str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def is_port_available(host: str, port: int) -> bool:
    bind_host = "0.0.0.0" if host in {"0.0.0.0", "::"} else host
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((bind_host, port))
        except OSError:
            return False
    return True


def choose_available_port(host: str, preferred_port: int, scan_limit: int = DEFAULT_PORT_SCAN_LIMIT) -> int:
    for candidate in range(preferred_port, preferred_port + scan_limit + 1):
        if is_port_available(host, candidate):
            return candidate
    raise RuntimeError(
        f"Unable to find an available port in range {preferred_port}-{preferred_port + scan_limit} for host {host}."
    )


def discover_ipv4_addresses() -> list[str]:
    addresses: set[str] = set()

    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET):
            address = sockaddr[0]
            if _is_publicish_ipv4(address):
                addresses.add(address)
    except socket.gaierror:
        pass

    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
            sock.connect(("8.8.8.8", 80))
            address = sock.getsockname()[0]
            if _is_publicish_ipv4(address):
                addresses.add(address)
    except OSError:
        pass

    return sorted(addresses, key=_ipv4_sort_key)


def build_launch_info(host: str, preferred_port: int, scan_limit: int = DEFAULT_PORT_SCAN_LIMIT) -> LaunchInfo:
    port = choose_available_port(host, preferred_port, scan_limit=scan_limit)
    access_urls = build_access_urls(host, port)
    browser_url = _select_browser_url(host, port, access_urls)
    return LaunchInfo(host=host, port=port, browser_url=browser_url, access_urls=access_urls)


def build_access_urls(host: str, port: int) -> list[str]:
    urls: list[str] = []

    def add(url: str) -> None:
        if url not in urls:
            urls.append(url)

    if host in {"127.0.0.1", "localhost"}:
        add(f"http://127.0.0.1:{port}/")
        add(f"http://localhost:{port}/")
        return urls

    if host in {"0.0.0.0", "::"}:
        for address in discover_ipv4_addresses():
            add(f"http://{address}:{port}/")
        add(f"http://127.0.0.1:{port}/")
        add(f"http://localhost:{port}/")
        return urls

    add(f"http://{host}:{port}/")
    if host not in {"127.0.0.1", "localhost"}:
        add(f"http://127.0.0.1:{port}/")
        add(f"http://localhost:{port}/")
    return urls


def _is_publicish_ipv4(address: str) -> bool:
    return bool(address) and not address.startswith("127.") and not address.startswith("169.254.")


def _ipv4_sort_key(address: str) -> tuple[int, tuple[int, int, int, int]]:
    ip = ipaddress.IPv4Address(address)
    octets = tuple(int(part) for part in address.split("."))

    if address.startswith("192.168."):
        return (0, octets)
    if address.startswith("10."):
        return (1, octets)
    if ip.is_private:
        return (2, octets)
    return (3, octets)


def _select_browser_url(host: str, port: int, access_urls: list[str]) -> str:
    if host in {"0.0.0.0", "::", "127.0.0.1", "localhost"}:
        return f"http://localhost:{port}/"
    return access_urls[0]
