"""Network-gated access to the frozen package and URL verifiers.

Created: 2026-10-30
Version: v2026.10.30-02
Purpose: Publication adapter (new code). The frozen verifiers in 2026_ICDE/
         query PyPI, npm and DNS whenever a name or host is not already in
         their evidence cache. This module constructs the same verifier
         classes, unchanged, but refuses any live query unless the caller
         passes allow_network=True or sets VULCHAIN_ALLOW_NETWORK=1.

Importing this module, or the frozen verifiers, performs no network access.
Verification definitions are not changed: cached evidence is read exactly as
the frozen code reads it, and an allowed live query runs the frozen code.
"""

import os
import sys
from pathlib import Path

ICDE = Path(__file__).resolve().parent / "2026_ICDE"
if str(ICDE) not in sys.path:
    sys.path.insert(0, str(ICDE))

import package_probe_validation  # noqa: E402  (frozen; stdlib only)


class NetworkDisabled(RuntimeError):
    """A live registry or DNS query was needed but not explicitly allowed."""


def network_allowed(allow_network=None):
    if allow_network is not None:
        return bool(allow_network)
    return os.environ.get("VULCHAIN_ALLOW_NETWORK") == "1"


def _refuse_registry(ecosystem, name):
    raise NetworkDisabled(f"registry lookup for {ecosystem}:{name} is not cached; "
                          "set VULCHAIN_ALLOW_NETWORK=1 to query PyPI/npm")


def package_verifier(db, fetch=None, allow_network=None):
    """Frozen PackageVerifier; live registry fetch only when explicitly allowed."""
    if fetch is None and not network_allowed(allow_network):
        fetch = _refuse_registry
    return package_probe_validation.PackageVerifier(db, fetch=fetch)


def url_verifier(db, source_dir, allow_network=None):
    """Frozen url_probe_validation.Verifier; live DNS only when explicitly allowed.

    Needs tldextract, dnspython and validators (requirements-verifiers.txt).
    """
    import url_probe_validation  # frozen; imported lazily for its third-party deps

    allowed = network_allowed(allow_network)

    class GatedVerifier(url_probe_validation.Verifier):
        def dns(self, host):
            cached = self.db.execute("SELECT 1 FROM dns_evidence WHERE host=?", (host,)).fetchone()
            if not cached and not allowed:
                raise NetworkDisabled(f"DNS lookup for {host} is not cached; "
                                      "set VULCHAIN_ALLOW_NETWORK=1 to query DNS")
            return super().dns(host)

    return GatedVerifier(db, Path(source_dir))
