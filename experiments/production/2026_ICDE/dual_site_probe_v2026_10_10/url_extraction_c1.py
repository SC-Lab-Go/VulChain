"""Created: 2026-10-11
Version: url-extract-v2026.10.11-c1 (change ID v2026.10.11-claude-08)
Purpose: versioned correction of URL extraction for Markdown links. The frozen extractor
(2026_ICDE/url_probe_validation.py, unchanged and hash-verified) matches https?://[^\\s<>"'`]+, which runs
through the '](' separator of a Markdown link whose text is itself a URL, e.g.
  [https://github.com/optuna/optuna](https://github.com/optuna/optuna)
yielding one malformed candidate that is never DNS-checked. This module runs the frozen extractor and
splits any candidate containing '](' into its link-text part and destination part, each trimmed with the
frozen trimming rules, keeping exact occurrence offsets and the frozen +/-160-character context window.
Parts that are not URL-like (no http(s):// or www. prefix) are dropped, as the frozen pattern would.
Validation (context exclusions, feeds, Tranco, PSL, DNS) is the frozen Verifier.validate, unchanged.
"""
import re
from url_probe_validation import extract_urls as frozen_extract_urls

POLICY = 'url-extract-v2026.10.11-c1'
URLISH = re.compile(r'(?:https?://|www\.)', re.I)

def trim(raw):
    # Same trimming as the frozen extractor.
    raw = raw.rstrip('.,;!')
    while raw.endswith(')') and raw.count(')') > raw.count('('):
        raw = raw[:-1]
    return raw.rstrip(']}')

def split_markdown(response, raw, start):
    """Yield (raw, start, end) parts of one frozen candidate."""
    if '](' not in raw:
        yield raw, start, start+len(raw); return
    pos = 0
    for piece in raw.split(']('):
        if piece and URLISH.match(piece):
            t = trim(piece)
            if t: yield t, start+pos, start+pos+len(t)
        pos += len(piece)+2

def classify(response):
    """Yield (frozen_index, raw, start, end, context, changed) for corrected candidates, in order."""
    for i, (raw, start, end, context) in enumerate(frozen_extract_urls(response)):
        parts = list(split_markdown(response, raw, start))
        changed = parts != [(raw, start, end)]
        for r, s, e in parts:
            yield i, r, s, e, response[max(0, s-160):min(len(response), e+160)], changed

def extract_urls(response):
    for _, r, s, e, ctx, _ in classify(response):
        yield r, s, e, ctx
