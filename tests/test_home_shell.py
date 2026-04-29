from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pandas as pd
import pytest


class _TagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.ids: dict[str, tuple[str, dict[str, str | None]]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        self.tags.append((tag, attr_map))
        element_id = attr_map.get("id")
        if element_id:
            self.ids[element_id] = (tag, attr_map)


def _parse_html(document: str) -> _TagCollector:
    parser = _TagCollector()
    parser.feed(document)
    return parser


def _class_tokens(attrs: dict[str, str | None]) -> set[str]:
    return set((attrs.get("class") or "").split())


def _find_tags(
    parser: _TagCollector,
    tag_name: str,
    **attrs: str,
) -> list[dict[str, str | None]]:
    matches: list[dict[str, str | None]] = []
    for tag, tag_attrs in parser.tags:
        if tag != tag_name:
            continue
        if all(tag_attrs.get(name) == value for name, value in attrs.items()):
            matches.append(tag_attrs)
    return matches


def _assert_has_class(
    parser: _TagCollector,
    tag_name: str,
    required_class: str,
    **attrs: str,
) -> None:
    matches = _find_tags(parser, tag_name, **attrs)
    assert matches, f"Expected <{tag_name}> with attributes {attrs!r}."
    assert any(required_class in _class_tokens(match) for match in matches), (
        f"Expected <{tag_name}> with attributes {attrs!r} to include class `{required_class}`."
    )


@pytest.fixture
def home_client(monkeypatch, load_module_or_fail, load_public_attr, app_config):
    create_app = load_public_attr("ashare_similarity.app", "create_app")
    runtime_module = load_module_or_fail("ashare_similarity.runtime")
    web_routes = load_module_or_fail("ashare_similarity.web.routes")

    class StoreStub:
        def list_cached_symbols(self, frequency: str) -> list[str]:
            if frequency == "daily":
                return ["999999", "600036", "601166"]
            return []

        def load_bars(self, symbol: str, frequency: str) -> pd.DataFrame:
            assert symbol == "600036"
            assert frequency == "daily"
            return pd.DataFrame({"date": [pd.Timestamp("2026-04-22")]})

    runtime = SimpleNamespace(
        config=app_config,
        store=StoreStub(),
        search_service=SimpleNamespace(),
        data_service=SimpleNamespace(),
        feature_service=SimpleNamespace(),
        index_service=SimpleNamespace(),
        context_service=SimpleNamespace(),
    )

    monkeypatch.setattr(runtime_module, "get_runtime", lambda: runtime)
    monkeypatch.setattr(web_routes, "get_runtime", lambda: runtime)

    app = create_app()
    app.state.runtime = runtime
    app.state.app_config = app_config

    with TestClient(app) as client:
        yield client


def test_home_page_renders_shell_contract(home_client):
    response = home_client.get("/")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/html")

    page = _parse_html(response.text)

    _assert_has_class(page, "div", "page-shell")
    _assert_has_class(page, "header", "hero")
    _assert_has_class(page, "main", "content-stack")
    _assert_has_class(page, "section", "analysis-grid")
    _assert_has_class(page, "section", "system-status-panel")
    _assert_has_class(page, "form", "search-form", id="search-form")
    _assert_has_class(page, "div", "status-box", id="status-box")
    _assert_has_class(page, "div", "chart", id="query-chart")
    _assert_has_class(page, "div", "match-list", id="balanced-list")
    _assert_has_class(page, "div", "match-list", id="shape-list")

    required_ids = {
        "search-form",
        "symbol-suggestions",
        "symbol-helper",
        "random-symbol-button",
        "prepare-symbol-button",
        "prepare-result",
        "status-box",
        "predict-button",
        "export-csv",
        "export-html",
        "system-status-updated",
        "system-status-cards",
        "system-status-details",
        "query-summary",
        "query-badges",
        "response-notices",
        "query-chart",
        "aggregate-table",
        "prediction-result",
        "balanced-title",
        "balanced-list",
        "shape-title",
        "shape-list",
    }
    assert required_ids <= set(page.ids), (
        "Homepage shell is missing one or more required DOM anchors for the productized UI."
    )

    controls = {
        attrs["name"]: (tag, attrs)
        for tag, attrs in page.tags
        if tag in {"input", "select"} and attrs.get("name")
    }
    assert controls["symbol"][0] == "input"
    assert controls["symbol"][1].get("type") == "text"
    assert controls["symbol"][1].get("list") == "symbol-suggestions"
    assert "required" in controls["symbol"][1]
    assert controls["end_date"][1].get("type") == "date"
    assert controls["frequency"][0] == "select"
    assert controls["window_size"][1].get("min") == "3"
    assert controls["window_size"][1].get("max") == "240"
    assert controls["top_k"][1].get("min") == "1"
    assert controls["top_k"][1].get("max") == "50"
    assert controls["search_scope"][0] == "select"

    export_csv = page.ids["export-csv"][1]
    export_html = page.ids["export-html"][1]
    for attrs in (export_csv, export_html):
        assert attrs.get("href") == "#"
        assert attrs.get("aria-disabled") == "true"
        assert "disabled" in _class_tokens(attrs)

    assert "empty-state" in _class_tokens(page.ids["balanced-list"][1])
    assert "empty-state" in _class_tokens(page.ids["shape-list"][1])


def test_home_page_renders_server_side_search_defaults(home_client):
    response = home_client.get("/")

    assert response.status_code == 200, response.text

    document = response.text
    assert 'name="symbol" value="600036"' in document
    assert 'name="end_date" value="2026-04-22"' in document
    assert 'name="window_size" value="10"' in document
    assert 'name="top_k" value="10"' in document
    assert '<option value="daily" selected>' in document
    assert '<option value="historical" selected>' in document


def test_home_page_uses_local_bundled_assets_in_expected_order(home_client):
    response = home_client.get("/")

    assert response.status_code == 200, response.text

    page = _parse_html(response.text)
    stylesheet_hrefs = [attrs.get("href") for attrs in _find_tags(page, "link", rel="stylesheet")]
    script_srcs = [attrs.get("src") for attrs in _find_tags(page, "script") if attrs.get("src")]

    assert any(str(href).startswith("/static/styles.css?v=") for href in stylesheet_hrefs)
    assert len(script_srcs) == 2
    assert str(script_srcs[0]).startswith("/static/vendor/echarts.min.js?v=")
    assert str(script_srcs[1]).startswith("/static/app.js?v="), (
        "Homepage should load the bundled chart vendor before the page app script."
    )

    asset_urls = [value for value in [*stylesheet_hrefs, *script_srcs] if value]
    assert not any(str(url).startswith(("http://", "https://", "//")) for url in asset_urls), (
        "Homepage shell should rely on packaged local assets instead of external CDNs."
    )


def test_template_and_frontend_script_dom_id_contract_stay_in_sync():
    from ashare_similarity.app import _static_dir
    from ashare_similarity.web.routes import template_dir

    template_path = Path(template_dir) / "index.html"
    script_path = Path(_static_dir()) / "app.js"

    template_text = template_path.read_text(encoding="utf-8")
    script_text = script_path.read_text(encoding="utf-8")

    template_ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', template_text))
    direct_dom_ids = set(re.findall(r'document\.getElementById\(["\']([A-Za-z0-9_-]+)["\']\)', script_text))
    render_target_ids = set(re.findall(r'renderMatches\(["\']([A-Za-z0-9_-]+)["\']', script_text))
    frontend_dom_ids = direct_dom_ids | render_target_ids

    missing_ids = frontend_dom_ids - template_ids
    assert not missing_ids, (
        "The homepage template is missing DOM anchors referenced by the frontend script: "
        f"{sorted(missing_ids)}"
    )
