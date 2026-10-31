package workflows

import (
	"errors"
	"fmt"
	"testing"

	"go.temporal.io/sdk/temporal"
)

func TestShortErrReportsActivityError(t *testing.T) {
	cause := temporal.NewApplicationError("bad JSON", "ValueError")
	own := temporal.NewNonRetryableApplicationError("every draft fabricated", "DraftRejected", cause)
	wrapped := fmt.Errorf("activity error: %w", own)

	cases := []struct {
		err  error
		want string
	}{
		{wrapped, "DraftRejected: every draft fabricated"},
		{temporal.NewApplicationError("dial tcp: no such host", "*url.Error"), "dial tcp: no such host"},
		{temporal.NewApplicationError("boom", "Error"), "boom"},
		{fmt.Errorf("outer: %w", errors.New("inner")), "inner"},
	}
	for _, c := range cases {
		if got := shortErr(c.err); got != c.want {
			t.Errorf("shortErr(%v) = %q, want %q", c.err, got, c.want)
		}
	}
}
