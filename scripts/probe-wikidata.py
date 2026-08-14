#!/usr/bin/env python3
"""Replay the SHIPPED producer templates against the live Wikidata Query Service.

Reads producers/wikidata.yml, substitutes {{keys}} exactly the way the sparql backend
does (literal = escaped quoted strings, iri = angle-bracketed), POSTs form-encoded per
the SPARQL 1.1 Protocol, and prints row counts plus a sample row. Run it after ANY
template edit — WDQS (Blazegraph) has sharp edges (NotMaterializedException when
mwapi output feeds aggregation or string BINDs; optimizer timeouts on property paths)
that only a live probe catches.

Usage: python3 scripts/probe-wikidata.py
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

USER_AGENT = "EmbabelRealmWikidata/0.1 probe (https://github.com/johnsonr/realm-wikidata)"

SAMPLE_KEYS = {
    "wikidataOrgByName": (["Broadcom", "Atlassian"], "literal"),
    "wikidataPersonByName": (["Tim Berners-Lee", "Grace Hopper"], "literal"),
    "wikidataRelationsByEntity": (
        ["http://www.wikidata.org/entity/Q555925", "http://www.wikidata.org/entity/Q757307"],
        "iri",
    ),
}


def serialize(keys: list[str], form: str) -> str:
    if form == "iri":
        return " ".join(f"<{k}>" for k in keys)
    return " ".join('"' + k.replace("\\", "\\\\").replace('"', '\\"') + '"' for k in keys)


def run(endpoint: str, query: str) -> dict:
    body = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.load(resp)
        except Exception as e:  # noqa: BLE001 — a probe reports, it doesn't triage
            if attempt == 2:
                raise
            print(f"    transient ({e}); retrying in 8s", flush=True)
            time.sleep(8)
    raise AssertionError("unreachable")


def main() -> int:
    producers = yaml.safe_load(
        (Path(__file__).resolve().parent.parent / "producers" / "wikidata.yml").read_text()
    )
    failures = 0
    for p in producers:
        name = p["name"]
        keys, form = SAMPLE_KEYS[name]
        declared_form = p.get("keyForm", "literal")
        if declared_form != form:
            print(f"FAIL {name}: probe assumes keyForm={form}, yml declares {declared_form}")
            failures += 1
            continue
        query = p["query"].replace("{{keys}}", serialize(keys, form))
        print(f"── {name} ({len(keys)} keys)", flush=True)
        try:
            result = run(p["endpoint"], query)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {name}: {e}")
            failures += 1
            continue
        rows = result["results"]["bindings"]
        key_var = p["keyVar"]
        echoed = {b[key_var]["value"] for b in rows if key_var in b}
        missing = [k for k in keys if k not in echoed]
        print(f"    {len(rows)} rows; keys echoed: {len(echoed)}/{len(keys)}")
        if rows:
            print("    sample:", {k: v["value"][:60] for k, v in rows[0].items()})
        if not rows:
            print(f"FAIL {name}: zero rows for keys that are known to match")
            failures += 1
        elif missing:
            print(f"FAIL {name}: no row echoed key(s) {missing} — the join would never form")
            failures += 1
    print("PROBE FAILED" if failures else "PROBE OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
