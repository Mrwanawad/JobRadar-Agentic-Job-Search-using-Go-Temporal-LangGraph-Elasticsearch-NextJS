from jobradar.dashboard import found_on_of, method_of
from jobradar.db import DB


def test_method_of_channels_and_ats():
    assert method_of("email", "", None) == "Cold email"
    assert method_of("linkedin", "", None) == "LinkedIn DM"
    assert method_of("manual", "Workable form, 12 screening Qs", None) == "Workable form"
    assert method_of("manual", "", "https://storyteller.applytojob.com/apply/x") == "JazzHR form"
    assert method_of("manual", "", "https://acme.com/careers/1") == "Careers-page form"


def test_found_on_of():
    assert found_on_of("manual", "gmail msg; LinkedIn feed post", None) == "LinkedIn post"
    assert found_on_of("manual", "Ashby; LinkedIn 4418825092", None) == "LinkedIn Jobs"
    assert found_on_of("wuzzuf", "wuzzuf app 1", None) == "Wuzzuf"
    assert found_on_of("manual", "cold email (Nasr City)", "mailto:x@y.com") == "Company research"


def test_upsert_process_updates_only_given_fields():
    db = DB(":memory:")
    pid = db.upsert_process("Acme", "AI Eng", stage="HR done", found_by="you", method="Cold email")
    assert db.upsert_process("Acme", "AI Eng", stage="Tech done", notes=None) == pid
    row = db.conn.execute("SELECT stage, found_by FROM processes WHERE id=?", (pid,)).fetchone()
    assert tuple(row) == ("Tech done", "you")
