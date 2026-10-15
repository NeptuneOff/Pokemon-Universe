"""Refresh the co-op adapter in the browser bundle, without changing other code."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "src/game.js"
source = target.read_text()
start = "// BEGIN COOP ADAPTER"
end = "// END COOP ADAPTER"
if source.count(start) != 1 or source.count(end) != 1:
    raise SystemExit("Expected exactly one pair of co-op adapter markers")
adapter = (root / "src/coop-client.inc.js").read_text()
target.write_text(source[: source.index(start)] + start + "\n" + adapter + "\n" + source[source.index(end) :])
