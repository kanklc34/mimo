from pathlib import Path


WEB = Path(__file__).resolve().parents[1] / "web"


def test_route_map_has_an_accessible_expanded_inspection_view():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'id="route-detail-dialog"' in html
    assert 'data-route-map="new"' in html
    assert 'data-detail-map="old"' in html
    assert 'data-detail-map="new"' in html
    assert 'id="close-route-detail"' in html
    assert 'id="detail-map"' in html
    assert 'aria-modal="true"' in html
    assert 'id="overview-map-switch"' in html
    assert 'data-overview-map="old"' in html
    assert 'data-overview-map="new"' in html
    assert '<details class="timeline-details">' in html
    assert '<details class="changes-details"' in html
    assert '"#close-route-detail"' in script
    assert '"#detail-map"' in script
    assert '"[data-route-map]"' in script
    assert '"[data-overview-map]"' in script
    assert '"#old-map-card"' in script
