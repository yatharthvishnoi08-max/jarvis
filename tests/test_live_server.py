import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

token = os.getenv("JARVIS_AUTH_TOKEN", "").strip()
BASE_URL = "http://localhost:8000"

print(f"Testing live server at {BASE_URL}...")

# 1. Root GET /
req = urllib.request.Request(f"{BASE_URL}/")
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode("utf-8")
    assert resp.status == 200
    assert "JARVIS Interface v3" in html or "root" in html
    print("✔ Test 1 PASSED: Root endpoint serves React PWA bundle.")

# 2. Unauthorized request
unauth_req = urllib.request.Request(f"{BASE_URL}/api/system/telemetry")
try:
    with urllib.request.urlopen(unauth_req) as resp:
        print("❌ Test 2 FAILED: Expected 401 Unauthorized but request succeeded.")
        assert False
except urllib.error.HTTPError as e:
    assert e.code == 401
    print(f"✔ Test 2 PASSED: Protected route rejected unauthorized access (HTTP {e.code}).")

# 3. Authenticated login
login_data = json.dumps({"token": token}).encode("utf-8")
login_req = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(login_req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    assert res["status"] == "authenticated"
    print("✔ Test 3 PASSED: Owner login authenticated successfully.")

# 4. Authenticated telemetry
auth_headers = {"Authorization": f"Bearer {token}"}
telem_req = urllib.request.Request(f"{BASE_URL}/api/system/telemetry", headers=auth_headers)
with urllib.request.urlopen(telem_req) as resp:
    telem = json.loads(resp.read().decode("utf-8"))
    assert "cpu_percent" in telem
    assert "ram_percent" in telem
    print(f"✔ Test 4 PASSED: Telemetry endpoint returned live host data (CPU: {telem['cpu_percent']}%, RAM: {telem['ram_percent']}%).")

# 5. Authenticated team roster
team_req = urllib.request.Request(f"{BASE_URL}/api/team", headers=auth_headers)
with urllib.request.urlopen(team_req) as resp:
    team = json.loads(resp.read().decode("utf-8"))
    assert len(team["employees"]) >= 3
    print(f"✔ Test 5 PASSED: Team roster loaded {len(team['employees'])} active employee agents.")

# 6. Authenticated voices
voices_req = urllib.request.Request(f"{BASE_URL}/api/voices", headers=auth_headers)
with urllib.request.urlopen(voices_req) as resp:
    vdata = json.loads(resp.read().decode("utf-8"))
    assert len(vdata["voices"]) >= 4
    print(f"✔ Test 6 PASSED: ElevenLabs voice personas loaded ({vdata['active_voice_id']}).")

# 7. Emergency stop
stop_req = urllib.request.Request(
    f"{BASE_URL}/api/emergency-stop",
    data=b"{}",
    headers={"Content-Type": "application/json", **auth_headers}
)
with urllib.request.urlopen(stop_req) as resp:
    sdata = json.loads(resp.read().decode("utf-8"))
    assert sdata["status"] == "emergency_stop_triggered"
    print("✔ Test 7 PASSED: Global emergency stop triggered and acknowledged.")

print("\n🎉 ALL LIVE SERVER END-TO-END TESTS PASSED SUCCESSFULLY!")
