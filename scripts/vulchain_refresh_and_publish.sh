#!/usr/bin/env bash
# Created: 2026-10-30  Version: v2026.10.30-03
# Purpose: Scheduled entry point. Always refreshes local results; publishes to
#          GitHub only through the deadline guard. A frozen or disabled
#          publication is a successful skip, so callers (for example a hook at
#          the end of daily_sync.sh) never fail because of GitHub.
# Usage:   bash scripts/vulchain_refresh_and_publish.sh
set -u
here=$(cd "$(dirname "$0")" && pwd)
py=${PYTHON:-python3}

"$py" -B "$here/refresh_results.py"
refresh_status=$?
if [ "$refresh_status" -ne 0 ]; then
    echo "Local refresh did not publish a new version (status $refresh_status); previous results kept."
fi

# Publication never changes the exit status of local research work.
"$py" -B "$here/publish_github.py" || echo "GitHub publication step reported a problem; local results unaffected."
exit "$refresh_status"
