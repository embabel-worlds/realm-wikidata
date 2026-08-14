# realm-wikidata

Wikidata enrichment for Embabel worlds: the open knowledge graph joined onto the
organizations and people you already hold, fetched live from the
[Wikidata Query Service](https://query.wikidata.org/) — CC0 data, no API key, no account.

```cypher
// What does the world's most heavily curated public graph know about this company?
MATCH (o:Organization {name:'Atlassian'})-[:HAS_WIKIDATA]->(w:WikidataOrg)
RETURN w.wdDescription, w.industryLabel, w.countryLabel, w.employees, w.lei, w.abn

// Who owns it, and what does it own?
MATCH (o:Organization {name:'Atlassian'})-[:HAS_WIKIDATA]->(w)-[:WD_RELATION]->(r)
RETURN r.relation, r.otherLabel, r.otherDescription
```

## What it provides

| Type | Joined from | Producer | What you get |
|---|---|---|---|
| `WikidataOrg` | `Organization` by `name` | `wikidataOrgByName` | Description, industry, country, HQ, founded, employees, website, ticker — and the identifier spine: LEI, Australian ABN |
| `WikidataPerson` | `Person` by `name` | `wikidataPersonByName` | Description, birth date, citizenship, website — deliberately minimal (see caveats) |
| `WikidataRelation` | `WikidataOrg` by entity IRI | `wikidataRelationsByEntity` | Ownership structure: parent, owner, subsidiaries, and what the org owns (acquired products included, patents excluded) |

The relations join chains from the card join — no second name search:
card resolves name → entity IRI, relations key on the IRI.

## Requirements

An Embabel `me` build with the `sparql` producer backend (2026-08-14 or later).
No credentials of any kind.

## Caveats — read before trusting a row

- **A name match is a search result, never an identity claim.** The cards carry
  `wdDescription` (and `birthDate` for people) precisely so a wrong match can be
  rejected. Most people in a personal graph are not notable; a search for a
  contact's name will happily return a famous namesake.
- **Cards keep one value per property.** Wikidata's multi-valued facts (several
  HQs, several industries) collapse to an arbitrary survivor on the card; anything
  that needs all values belongs on the relations join.
- **Values are "truthy" statements** — Wikidata's current preferred-rank values,
  not history.
- **The public endpoint is shared infrastructure.** Batches are bounded, results
  cached for a day, and the User-Agent identifies this realm per Wikimedia policy.
  Expect the occasional slow or refused query at peak times; the producer reports
  a failed fetch rather than pretending the entity is unknown.

## Template maintenance

The SPARQL lives in `producers/wikidata.yml` and has been shaped around real WDQS
(Blazegraph) limitations — templates are FLAT because mwapi-derived bindings crash
aggregation and string BINDs (`NotMaterializedException`), and every mwapi output
variable needs a required triple before use. After ANY template edit, replay the
shipped templates live:

```bash
python3 scripts/probe-wikidata.py
```
