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


def test_constraint_editing_uses_plain_language_form_controls_not_json():
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert 'id="constraint-list"' in html
    assert 'id="add-constraint-type"' in html
    assert 'id="add-constraint"' in html
    assert 'id="constraints"' not in html
    assert 'JSON\'u düzenle' not in html


def test_dashboard_opens_a_guided_workflow_instead_of_showing_everything():
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert 'id="start-workflow"' in html
    assert 'id="workflow-dialog"' in html
    assert 'class="panel constraints-panel" hidden' in html
    assert 'class="dashboard-side"' in html


def test_previous_plan_is_only_offered_after_a_replan_and_demo_data_is_labeled():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert "SENTETİK GÜN PLANI" in html
    assert "Sentetik duraklar" in html
    assert "state.hasComparison" in script
    assert 'data-detail-map="old"' in html


def test_map_labels_match_courier_colors_and_current_plan_state():
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert 'id="map-legend"' in html
    assert "YENİ PLAN" not in html
    assert "app.js?v=" in html
    assert html.count('id="reset-plan"') == 1
    assert "Başa dön" not in html


def test_stop_details_appear_at_selected_pin_and_follow_selected_plan():
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert "showStopTooltip" in script
    assert "visitForStop(stop.dataset.stopId, plan)" in script
    assert "state.detailMap === \"old\"" in script


def test_unavailable_courier_and_transferred_stops_are_explained():
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert "Devre dışı" in script
    assert "durak aktarıldı" in script


def test_initial_plan_uses_ready_state_instead_of_zero_change_report():
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert "Başlangıç planı hazır" in script
    assert "henüz devir yapılmadı" in script
    assert "state.hasComparison" in script


def test_overview_stop_selection_anchors_label_to_the_selected_stop():
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert "showStopDetails(stop.dataset.stopId, stop" in script
    assert "showStopTooltip(stopCircle" in script


def test_stop_tooltip_closes_when_clicking_elsewhere():
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'document.addEventListener("click", closeStopTooltipOnOutsideClick)' in script
