"""Application timeline built ONLY from what the farmer reported. Nothing here is an official status; the 'decision' step is never marked official."""
STAGES = ["prepared", "submitted", "under_review", "decision"]
STATUS_STAGE = {"prepared": 0, "submitted": 1, "under_review": 2, "approved": 3, "received": 3, "rejected": 3}
DISCLAIMER = "Every step is reported by you or your helper. It is not an official government status. Only an official notice or portal record can confirm an application's outcome."

def build(events):
    """events: [{status, reference_number, at}] oldest first (at = ISO string or None)."""
    reached = max([STATUS_STAGE.get(e["status"], -1) for e in events] or [-1]); steps = []
    for i, sid in enumerate(STAGES):
        ev = next((e for e in events if STATUS_STAGE.get(e["status"]) == i), None)
        steps.append({"id": sid, "reached": i <= reached, "date": (ev["at"] or "")[:10] if ev else None, "source": "self-reported", "official_confirmation": False})
    ref = next((e["reference_number"] for e in reversed(events) if e.get("reference_number")), "")
    last = events[-1]["status"] if events else None
    return {"steps": steps, "current": STAGES[reached] if reached >= 0 else None, "reference_number": ref,
            "decision_as_reported": last if last in ("approved", "received", "rejected") else None, "disclaimer": DISCLAIMER}
