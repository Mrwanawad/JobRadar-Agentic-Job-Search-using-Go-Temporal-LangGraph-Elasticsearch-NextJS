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


def test_host_allowed_blocks_dns_rebinding():
    from jobradar.dashboard import host_allowed

    for ok in ("127.0.0.1:8765", "localhost:8765", "LOCALHOST", "[::1]:8765", "[::1]"):
        assert host_allowed(ok), ok
    for bad in (None, "", "attacker.example", "attacker.example:8765", "127.0.0.1.nip.io:8765"):
        assert not host_allowed(bad), bad


def test_server_rejects_foreign_host_header():
    import threading

    import httpx

    from jobradar.dashboard import serve

    srv = serve(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        assert httpx.get(base + "/").status_code == 200
        r = httpx.get(base + "/api/snapshot", headers={"Host": "attacker.example"})
        assert r.status_code == 403
    finally:
        srv.shutdown()


def test_link_only_renders_http_urls():
    from jobradar.dashboard import PAGE

    assert r'/^https?:\/\//i.test(url ?? "")' in PAGE.read_text(encoding="utf-8")
