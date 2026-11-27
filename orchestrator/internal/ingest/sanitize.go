package ingest

import (
	"regexp"
	"strings"
)

// StripHidden cuts HTML comments and elements hidden by attribute or inline style out of a
// posting, leaving an invisible marker (U+E000 kind U+E001) where text was. It is a
// line-for-line port of jobradar/guard/sanitize.py strip_hidden_html, checked against the
// same cases (tests/fixtures/golden/hidden_html.json): text an attacker hides from people
// must not reach a model, in lite or platform mode.
func StripHidden(s string) string {
	if !strings.Contains(s, "<") {
		return s
	}
	s = reComment.ReplaceAllStringFunc(s, func(m string) string {
		if strings.Trim(m, "<!-> \n\t") != "" {
			return hiddenMark("comment")
		}
		return ""
	})
	var out strings.Builder
	pos := 0
	for {
		loc := reHTMLTag.FindStringSubmatchIndex(s[pos:])
		if loc == nil {
			out.WriteString(s[pos:])
			return out.String()
		}
		start, end := pos+loc[0], pos+loc[1]
		closing := loc[3] > loc[2]
		name := strings.ToLower(s[pos+loc[4] : pos+loc[5]])
		attrs := s[pos+loc[6] : pos+loc[7]]
		kind := ""
		if !closing {
			kind = hiddenKind(attrs)
		}
		if kind == "" {
			out.WriteString(s[pos:end])
			pos = end
			continue
		}
		out.WriteString(s[pos:start])
		if voidTags[name] || strings.HasSuffix(strings.TrimRight(attrs, " \t\n\r\f\v"), "/") {
			pos = end
			continue
		}
		stop := matchingEnd(s, name, end)
		if strings.TrimSpace(reHTMLTag.ReplaceAllString(s[end:stop], "")) != "" {
			out.WriteString(hiddenMark(kind))
		}
		pos = stop
	}
}

func hiddenMark(kind string) string { return "\ue000" + kind + "\ue001" }

func hiddenKind(attrs string) string {
	a := strings.ToLower(attrs)
	for _, h := range hiddenRules {
		if h.re.MatchString(a) {
			return h.kind
		}
	}
	return ""
}

// matchingEnd returns the index just past the end tag closing the element opened before
// start, or len(s) when it is never closed.
func matchingEnd(s, name string, start int) int {
	depth := 1
	for _, t := range reHTMLTag.FindAllStringSubmatchIndex(s[start:], -1) {
		if strings.ToLower(s[start+t[4]:start+t[5]]) != name {
			continue
		}
		if t[3] > t[2] {
			depth--
			if depth == 0 {
				return start + t[1]
			}
		} else if !strings.HasSuffix(strings.TrimRight(s[start+t[6]:start+t[7]], " \t\n\r\f\v"), "/") {
			depth++
		}
	}
	return len(s)
}

var (
	reComment = regexp.MustCompile(`<!--[\s\S]*?-->`)
	reHTMLTag = regexp.MustCompile(`<(/?)([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>`)
	voidTags  = map[string]bool{
		"area": true, "base": true, "br": true, "col": true, "embed": true, "hr": true,
		"img": true, "input": true, "link": true, "meta": true, "source": true, "track": true,
		"wbr": true,
	}
	hiddenRules = []struct {
		kind string
		re   *regexp.Regexp
	}{
		{"display-none", regexp.MustCompile(`display\s*:\s*none`)},
		{"invisible", regexp.MustCompile(`visibility\s*:\s*hidden|opacity\s*:\s*0(?:\.0+)?(?:[;\s"']|$)`)},
		{"tiny-font", regexp.MustCompile(`font-size\s*:\s*(?:0|1px|0?\.\d+[a-z%]*)(?:[;\s"']|$)`)},
		{"white-text", regexp.MustCompile(`(?:^|[;\s"'])color\s*:\s*(?:#fff\b|#ffffff\b|white\b|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))`)},
		{"offscreen", regexp.MustCompile(`(?:left|top|text-indent)\s*:\s*-\d{3,}`)},
		{"aria-hidden", regexp.MustCompile(`aria-hidden\s*=\s*["']?true`)},
		{"hidden-attr", regexp.MustCompile(`(?:^|\s)hidden(?:\s|=|$)`)},
	}
)
