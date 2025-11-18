import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)



from fastapi.testclient import TestClient
import app.main as main


class DummyLLM:
    def invoke(self, messages):
        return type("Resp", (), {
            "content": '{"evidence": "dummy evidence", "recommendation": "dummy recommendation"}'
        })


main.llm = DummyLLM()
client = TestClient(main.app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_triage_invoke_refund_request():
    payload = {
        "ticket_text": "Hi, my order ORD1002 is late and I want a refund.",
        "order_id": None,
    }

    resp = client.post("/triage/invoke", json=payload)
    assert resp.status_code == 200

    data = resp.json()

    assert data["order_id"] == "ORD1002"
    assert data["issue_type"] == "refund_request"
    assert data["evidence"] == "dummy evidence"
    assert data["recommendation"] == "dummy recommendation"
    assert data["order"]["customer_name"] == "David Lee"
    assert "David Lee" in data["reply_text"]
    assert "ORD1002" in data["reply_text"]
