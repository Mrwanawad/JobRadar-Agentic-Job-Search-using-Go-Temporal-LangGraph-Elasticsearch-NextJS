"""Rebuild evals/data/postings.jsonl from labels.csv and the platform's Postgres.

Labels are by hand, for the synthetic persona in persona.yaml. Postings are real public job
ads; descriptions are truncated. Only needed when labels change:

    DATABASE_URL=postgres://jobradar:jobradar@localhost:5432/jobradar \
        uv run --extra platform python -m evals.build_dataset
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DATA = Path(__file__).parent / "data"
DESC_CHARS = 12_000  # sponsorship lines often sit at the end


def main() -> None:
    labels = list(csv.DictReader((DATA / "labels.csv").open(encoding="utf-8")))
    uids = [r["uid"] for r in labels]
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as db:
        rows = db.execute(
            "SELECT uid, source, company, title, location, remote, url, description, posted_at"
            " FROM jobs WHERE uid = ANY(%s)",
            (uids,),
        ).fetchall()
    jobs = {r["uid"]: r for r in rows}
    missing = [u for u in uids if u not in jobs]
    if missing:
        raise SystemExit(f"not in the database: {missing}")
    with (DATA / "postings.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for lab in labels:
            j = jobs[lab["uid"]]
            j["description"] = (j["description"] or "")[:DESC_CHARS]
            j["posted_at"] = j["posted_at"].isoformat() if j["posted_at"] else None
            j["label"] = {"keep": lab["keep"] == "1", "band": lab["band"], "note": lab["note"]}
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"wrote {len(labels)} postings")


if __name__ == "__main__":
    main()
