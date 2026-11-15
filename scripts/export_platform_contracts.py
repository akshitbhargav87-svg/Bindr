"""Regenerate the owned request-schema packet from the actual v2 routers."""

import json
from pathlib import Path
from backend.app.main import app


def main():
    spec = app.openapi()
    paths = {
        p: v
        for p, v in spec["paths"].items()
        if p.startswith("/api/v2/") or p == "/api/v2/account"
    }
    components = spec.get("components", {}).get("schemas", {})
    needed = set()

    def refs(value):
        if isinstance(value, dict):
            if "$ref" in value:
                needed.add(value["$ref"].split("/")[-1])
            for child in value.values():
                refs(child)
        elif isinstance(value, list):
            for child in value:
                refs(child)

    refs(paths)
    while True:
        previous = set(needed)
        for name in previous:
            refs(components[name])
        if needed == previous:
            break
    result = {
        "openapi": spec["openapi"],
        "info": {
            "title": "Bindr platform request schemas; HTTP response examples separate",
            "version": "2-packet-1",
        },
        "paths": paths,
        "components": {"schemas": {name: components[name] for name in sorted(needed)}},
        "x-auth-note": "Existing verified account cookies, expected-account, Origin and CSRF are mandatory. Explicit capture capabilities and verified provider signatures have their own restricted seams; see API_V2_PACKET.md.",
    }
    output = (
        Path(__file__).resolve().parents[1] / "tests/contracts/platform/openapi-v2.json"
    )
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("Wrote request schemas for", len(paths), "v2 paths.")


if __name__ == "__main__":
    main()
