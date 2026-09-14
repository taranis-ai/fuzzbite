"""Dependency-free checks, run outside the checkout against an installed wheel."""

import importlib.metadata
from pathlib import Path

import fuzzbite

package = Path(fuzzbite.__file__).resolve().parent
assert "site-packages" in str(package), package
assert (package / "py.typed").is_file()
assert (package / "_native.pyi").is_file()
assert importlib.metadata.version("fuzzbite") == "0.1.1"
assert fuzzbite.hash(b"hello world") == "3:iKFSMPn:rJPn"
left = "12288:+ySwl5P+C5IxJ845HYV5sxOH/cccccccei:+Klhav84a5sxJ"
right = "12288:+yUwldx+C5IxJ845HYV5sxOH/cccccccex:+glvav84a5sxK"
assert fuzzbite.compare(left, right) == 88
matcher = fuzzbite.Matcher(left)
assert matcher.find_match([]) is None
assert matcher.find_match([right]) is None
assert matcher.find_match([right, left]) == (1, 100)
assert matcher.find_match([right, left], threshold=88) == (0, 88)
assert matcher.find_match([left, "invalid"]) == (0, 100)
try:
    matcher.find_match(["invalid"])
except ValueError:
    pass
else:
    raise AssertionError("invalid fingerprint accepted")
print(f"Installed fuzzbite smoke passed: {package}")
