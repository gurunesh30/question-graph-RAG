"""Centralised Cypher query library.

Every Cypher statement used by the pipeline lives here as a constant so
that the queries are easy to audit, version-control, and unit-test.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Phase 2 - ingestion helpers
# ---------------------------------------------------------------------------

# Generic node count per label, used by smoke tests and ops dashboards.
NODE_COUNTS_QUERY = """
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS n
ORDER BY n DESC
"""

# Server component info, used by connection verification.
SERVER_INFO_QUERY = """
CALL dbms.components() YIELD name, versions, edition
RETURN name, versions, edition
"""

# Lightweight round-trip used by connection verification.
PING_QUERY = "RETURN 1 AS ok"

# ---------------------------------------------------------------------------
# Phase 4 - centrality scoring
# ---------------------------------------------------------------------------

# Per-concept degree computed from the IS_A edge count.  We include both
# in- and out-degree to capture the full extent of "factual" attachment.
DEGREE_CENTRALITY_QUERY = """
MATCH (c:concept)
OPTIONAL MATCH (c)-[r_in:IS_A]->(t_in:textual)
OPTIONAL MATCH (t_out:textual)-[r_out:IS_A]->(c)
WITH c,
     count(DISTINCT t_in)  AS out_degree,
     count(DISTINCT t_out) AS in_degree
RETURN c.name      AS concept,
       (out_degree + in_degree) AS degree
ORDER BY degree DESC
"""

# Min/Max degree bounds across the whole graph.
DEGREE_BOUNDS_QUERY = """
MATCH (c:concept)
WITH c, size((c)-[:IS_A]-()) AS deg
RETURN min(deg) AS min_deg,
       max(deg) AS max_deg
"""

# Edge projection for PageRank.  Only the structural relationship types
# are included so the random walk stays bounded to the knowledge graph.
PAGERANK_PROJECT_QUERY = """
MATCH (a)-[r]->(b)
WHERE (a:concept OR a:hierarchy OR a:textual)
  AND (b:concept OR b:hierarchy OR b:textual)
  AND type(r) IN ['IS_A', 'INCLUDE_IN', 'PART_OF']
RETURN elementId(a) AS src, elementId(b) AS dst
"""

# Concept nodes with their elementIds, used to build the PageRank integer
# index (Neo4j 5.x elementId() returns strings).
CONCEPT_ELEMENT_IDS_QUERY = """
MATCH (n)
WHERE n:concept OR n:hierarchy OR n:textual
RETURN elementId(n) AS eid, labels(n)[0] AS label, n.name AS name
"""

# Batch upsert of degree, centrality, and difficulty onto each concept.
UPSERT_DIFFICULTY_QUERY = """
UNWIND $rows AS row
MATCH (c:concept {name: row.concept})
SET c.degree     = row.degree,
    c.centrality = row.centrality,
    c.difficulty = row.difficulty
RETURN count(c) AS updated
"""

# ---------------------------------------------------------------------------
# Phase 5 - retrieval
# ---------------------------------------------------------------------------

DIFFICULTY_BAND_QUERY = """
MATCH (c:concept)
WHERE c.difficulty >= $min_b AND c.difficulty < $max_b
RETURN c.name      AS concept,
       c.difficulty AS difficulty,
       c.centrality AS centrality
ORDER BY c.centrality DESC
LIMIT $limit
"""

SUBGRAPH_EXPANSION_QUERY = """
MATCH (c:concept {name: $concept_name})
OPTIONAL MATCH (t:textual)-[:IS_A]->(c)
OPTIONAL MATCH (c)-[:INCLUDE_IN]->(h:hierarchy)
RETURN c.name       AS concept,
       collect(DISTINCT t.name) AS textual_facts,
       collect(DISTINCT h.name) AS hierarchy_parents
"""