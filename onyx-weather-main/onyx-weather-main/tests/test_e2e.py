import sys
import requests
import json
import websocket

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8080"

def test_all():
    print("=" * 60)
    print("Testing VayuDrishti Platform HTTP & WebSocket Endpoints")
    print("=" * 60)

    # 1. Test HTML Pages
    for path in ["/", "/admin", "/citizen"]:
        res = requests.get(f"{BASE_URL}{path}")
        assert res.status_code == 200, f"Failed for {path}"
        assert len(res.text) > 500
        print(f"✓ HTML Route {path}: OK (200, {len(res.text)} bytes)")

    # 2. Test Static Assets
    for asset in [
        "/static/css/styles.css",
        "/static/js/map.js",
        "/static/js/charts.js",
        "/static/js/app.js",
        "/static/js/admin.js",
        "/static/js/citizen.js"
    ]:
        res = requests.get(f"{BASE_URL}{asset}")
        assert res.status_code == 200, f"Failed for {asset}"
        print(f"✓ Static Asset {asset}: OK (200)")

    # 3. Test Analytics Summary & Timeline
    sum_res = requests.get(f"{BASE_URL}/api/analytics/summary").json()
    assert sum_res["total_reports"] > 0
    assert "event_distribution" in sum_res
    assert len(sum_res["radar_stations"]) >= 10
    print(f"✓ Analytics Summary: OK ({sum_res['total_reports']} reports, {sum_res['total_verified']} verified, {len(sum_res['radar_stations'])} radar stations)")

    time_res = requests.get(f"{BASE_URL}/api/analytics/timeline").json()
    assert "timeline" in time_res
    print(f"✓ Analytics Timeline: OK ({len(time_res['timeline'])} hourly buckets)")

    # 4. Test Multi-Dimensional Filtering
    # Event filter
    rf_res = requests.get(f"{BASE_URL}/api/reports?event_type=rainfall").json()
    print(f"✓ Filter Event (rainfall): OK ({rf_res['total']} matched)")

    # State filter
    mh_res = requests.get(f"{BASE_URL}/api/reports?state=Maharashtra").json()
    print(f"✓ Filter State (Maharashtra): OK ({mh_res['total']} matched)")

    # Status filter
    fk_res = requests.get(f"{BASE_URL}/api/reports?status=fake_misleading").json()
    print(f"✓ Filter Status (fake_misleading): OK ({fk_res['total']} matched)")

    # Date preset filter
    d_res = requests.get(f"{BASE_URL}/api/reports?preset_range=24h").json()
    print(f"✓ Filter Preset Date (24h): OK ({d_res['total']} matched)")

    # 5. Test Citizen AI Preview & Submission
    prev_res = requests.post(f"{BASE_URL}/api/citizen/preview", json={
        "text": "Severe lightning thunderstorm and dark clouds in Delhi NCR #IMD",
        "city": "Delhi",
        "state": "Delhi"
    }).json()
    assert prev_res["predicted_event_type"] == "thunderstorm"
    assert prev_res["ai_confidence_pct"] >= 70.0
    print(f"✓ Citizen AI Real-time Preview: OK (Predicted: {prev_res['predicted_event_type']}, Confidence: {prev_res['ai_confidence_pct']}%)")

    sub_res = requests.post(f"{BASE_URL}/api/citizen/submit", json={
        "author_name": "Ravi Teja",
        "text": "Intense rain shower with 40mm downpour in Hyderabad Jubilee Hills #IMD #HyderabadRains",
        "city": "Hyderabad",
        "state": "Telangana",
        "lat": 17.4300,
        "lon": 78.4100
    }).json()
    assert sub_res["success"] is True
    report_id = sub_res["report"]["id"]
    print(f"✓ Citizen Report Submission: OK (Report ID: {report_id}, Status: {sub_res['report']['verification_status']})")

    # 6. Test Admin CAP Alert Broadcast
    alert_res = requests.post(f"{BASE_URL}/api/admin/broadcast-alert", json={
        "title": "Red Alert: Severe Cyclone Landfall Warning",
        "event_type": "cyclone",
        "severity": "Red Alert Emergency",
        "state": "Odisha",
        "districts": ["Puri", "Bhadrak", "Balasore"],
        "instructions": "Evacuate coastal vulnerable zones, suspend maritime operations.",
        "valid_hours": 36
    }).json()
    assert alert_res["success"] is True
    print(f"✓ Admin CAP Alert Broadcast: OK (Alert ID: {alert_res['alert_id']})")

    # 7. Test Admin Scenario Trigger
    scen_res = requests.post(f"{BASE_URL}/api/admin/trigger-scenario", json={
        "scenario": "mumbai_cloudburst"
    }).json()
    assert scen_res["success"] is True
    assert scen_res["generated_reports_count"] >= 2
    print(f"✓ Admin Scenario Simulation (mumbai_cloudburst): OK ({scen_res['generated_reports_count']} reports generated)")

    # 8. Test Admin Moderation & Audit Log
    mod_res = requests.post(f"{BASE_URL}/api/admin/moderate", json={
        "report_id": report_id,
        "action": "approve",
        "admin_user": "IMD_Senior_Duty_Officer",
        "reason": "Corroborated by Jubilee Hills AWS ground sensor"
    }).json()
    assert mod_res["success"] is True
    print(f"✓ Admin Moderation Workflow: OK (Status -> {mod_res['new_status']})")

    logs_res = requests.get(f"{BASE_URL}/api/admin/moderation-logs").json()
    assert len(logs_res["logs"]) > 0
    print(f"✓ Moderation Audit Trail: OK ({len(logs_res['logs'])} audit records)")

    # 9. Test Data Exports
    csv_res = requests.get(f"{BASE_URL}/api/export/csv")
    assert csv_res.status_code == 200
    assert "id,source" in csv_res.text
    print(f"✓ CSV Export: OK ({len(csv_res.text)} bytes)")

    json_res = requests.get(f"{BASE_URL}/api/export/json")
    assert json_res.status_code == 200
    assert "data" in json_res.json()
    print(f"✓ JSON Export: OK ({json_res.json()['count']} exported items)")

    # 10. Test WebSocket Hub
    ws = websocket.create_connection("ws://127.0.0.1:8080/api/stream/ws", timeout=5)
    ws.send("ping")
    resp = ws.recv()
    assert resp == "pong"
    ws.close()
    print("✓ WebSocket Live Stream Connection: OK (Ping/Pong verified)")

    print("=" * 60)
    print("ALL 10 END-TO-END VERIFICATION SUITES PASSED FLAWLESSLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_all()
