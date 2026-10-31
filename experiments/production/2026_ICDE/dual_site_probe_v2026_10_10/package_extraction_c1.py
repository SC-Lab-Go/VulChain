"""Created: 2026-10-11
Version: pkg-extract-v2026.10.11-c1 (change ID v2026.10.11-claude-07)
Purpose: versioned correction of install-command package extraction. The frozen extractor
(2026_ICDE/package_probe_validation.py, unchanged and still hash-verified) tokenizes install arguments
with shlex.split() without comment handling, so words in a trailing shell comment
("pip install redis  # for scalability (optional)") become package candidates.
This module runs the frozen extractor and drops only install candidates that start inside an unquoted
shell comment on the same install line. Imports, dependency maps and all other candidates are unchanged.
"""
import re
from package_probe_validation import extract_packages as frozen_extract_packages

POLICY = 'pkg-extract-v2026.10.11-c1'
# Identical to the frozen install pattern.
INSTALL = re.compile(r'\b(pip3?\s+install|npm\s+(?:install|i)|yarn\s+add|pnpm\s+add)\s+([^\n;&|`]+)')

def comment_start(segment):
    """Index of an unquoted '#' that begins a shell comment (at start or after whitespace), else None."""
    quote = None
    for i, ch in enumerate(segment):
        if quote:
            if ch == quote: quote = None
        elif ch in ('"', "'"): quote = ch
        elif ch == '#' and (i == 0 or segment[i-1].isspace()): return i
    return None

def shell_comment_spans(text):
    spans = []; offset = 0
    for line in text.splitlines(keepends=True):
        install = INSTALL.search(line)
        if install:
            at = comment_start(install[2])
            if at is not None: spans.append((offset + install.start(2) + at, offset + len(line)))
        offset += len(line)
    return spans

def classify(text):
    """Yield (candidate, excluded) for every frozen candidate, in frozen order."""
    spans = shell_comment_spans(text)
    for c in frozen_extract_packages(text):
        excluded = c['construct'] == 'install' and any(a <= c['start_offset'] < b for a, b in spans)
        yield c, excluded

def extract_packages(text):
    for c, excluded in classify(text):
        if not excluded: yield c
