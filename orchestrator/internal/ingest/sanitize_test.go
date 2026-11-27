package ingest

import (
	"encoding/json"
	"testing"
)

// TestHiddenParityWithPython runs HTMLToText (and so StripHidden) on the hidden-content
// cases whose expected text the Python side wrote (scripts/golden_jobs.py).
func TestHiddenParityWithPython(t *testing.T) {
	var cases []struct {
		Input string `json:"input"`
		Want  string `json:"want"`
	}
	if err := json.Unmarshal(readFixture(t, "golden/hidden_html.json"), &cases); err != nil {
		t.Fatal(err)
	}
	if len(cases) < 10 {
		t.Fatalf("only %d cases", len(cases))
	}
	for _, c := range cases {
		if got := HTMLToText(c.Input); got != c.Want {
			t.Errorf("HTMLToText(%q)\n got %q\nwant %q", c.Input, got, c.Want)
		}
	}
}
