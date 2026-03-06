"""Campground search helper.

Usage:
    python -m src.search "Yosemite"
    python -m src.search "Pfeiffer Big Sur"
"""

from __future__ import annotations

import sys

from . import recreationgov as api


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.search <campground name>", file=sys.stderr)
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"Searching for: {query!r}\n")

    try:
        results = api.search_campgrounds(query)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("No results found.")
        return

    for r in results:
        entity_id = r.get("entity_id", "?")
        name = r.get("name", "Unknown")
        parent = r.get("parent_name", "")
        print(f"  {entity_id:>10}  {name}" + (f"  ({parent})" if parent else ""))


if __name__ == "__main__":
    main()
