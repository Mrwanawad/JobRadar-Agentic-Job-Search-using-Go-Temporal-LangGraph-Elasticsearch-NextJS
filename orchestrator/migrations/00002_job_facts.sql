-- +goose Up
-- Quarantined extraction (jobradar/guard/extract.py): typed facts per posting, written by a
-- model that never sees a CV, read by the screening and writing models instead of the
-- posting text. Jobs are shared by every profile, so facts are paid for once per posting.
ALTER TABLE jobs ADD COLUMN facts JSONB;

-- +goose Down
ALTER TABLE jobs DROP COLUMN facts;
