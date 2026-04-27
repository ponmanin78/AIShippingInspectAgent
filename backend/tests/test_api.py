from __future__ import annotations

from app.models.domain import JobStatus


async def test_submit_processes_invoice_and_allows_approval(client):
    invoice = (
        "INVOICE 1048\n"
        "Supplier: Northline Freight Services\n"
        "Fleet: Commercial tractor trailer\n"
        "Vehicle VIN: 1FT8W3BT9NEC00001\n"
        "Bill of Lading: BOL-99128\n"
        "Cargo Value: 48250.00 USD\n"
        "Shipment Date: 2026-04-27\n"
    )
    submit = await client.post(
        "/submit",
        data={"region": "US", "submitter_email": "owner@example.com"},
        files={"file": ("mock_invoice.txt", invoice, "text/plain")},
    )
    assert submit.status_code == 202
    job_id = submit.json()["job_id"]

    job_response = await client.get(f"/jobs/{job_id}")
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["status"] == JobStatus.HUMAN_REVIEW.value
    assert job["fleet_type"] == "Commercial"
    assert job["report"]["recommendation"] in {"APPROVE", "REQUEST_MORE_INFO", "REJECT"}

    review = await client.post(
        f"/review/{job_id}",
        json={"action": "APPROVE", "comments": "Inspection complete."},
    )
    assert review.status_code == 200
    assert review.json()["job"]["status"] == JobStatus.APPROVED.value
    assert review.json()["notification"]["type"] == "approval"


async def test_metrics_returns_dashboard_counts(client):
    await client.post(
        "/submit",
        data={"region": "US"},
        files={"file": ("mock_invoice.txt", "INVOICE\nCommercial cargo vehicle VIN 123", "text/plain")},
    )

    metrics = await client.get("/metrics")
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["total_requests"] == 1
    assert payload["pending_reviews"] == 1
    assert "pass_count" in payload
    assert "fail_count" in payload

