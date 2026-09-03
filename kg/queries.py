"""Cypher query library for the KAQG Centrality Engine.

All queries are read against Neo4j AuraDB via the `neo4j` Python driver and
return plain Python dictionaries that the central scoring pipeline
(``kg/centrality.py``) consumes.

The query set is intentionally small and explicit so that the scoring pipeline
can stay testable without requiring a live database connection.
"""

# Degree centrality counts both incoming and outgoing IS_A relationships that
# touch a `concept` node.  The textual nodes connected to a concept are
# treated as evidence of the concept's breadth.
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

# PageRank weights relationships in the concept <-> textual subgraph.
# We project only the relevant edge types so that the random walk is bounded
# to knowledge-graph structure (PART_OF / IS_A / INCLUDE_IN).
PAGERANK_PROJECT_QUERY = """
MATCH (a)-[r]->(b)
WHERE (a:concept OR a:hierarchy OR a:textual)
  AND (b:concept OR b:hierarchy OR b:textual)
  AND type(r) IN ['IS_A','INCLUDE_IN','PART_OF']
RETURN id(a) AS src, id(b) AS dst
"""

# Find the highest and lowest raw centrality scores so that the Python
# normalization step can map them into IRT difficulty range [0.1, 1.0].
CENTRALITY_BOUNDS_QUERY = """
MATCH (c:concept)
WHERE c.centrality IS NOT NULL
RETURN min(c.centrality) AS min_v,
       max(c.centrality) AS max_v
"""

# Difficulty filter + neighborhood expansion.  Used by the Phase 5
# subgraph sampler.  ``$min_b`` and ``$max_b`` are IRT difficulty bounds.
DIFFICULTY_BAND_QUERY = """
MATCH (c:concept)
WHERE c.difficulty >= $min_b AND c.difficulty < $max_b
RETURN c.name      AS concept,
       c.difficulty AS difficulty,
       c.centrality AS centrality
ORDER BY c.centrality DESC
LIMIT $limit
"""

# Pull a target concept together with its textual facts and parent hierarchy.
SUBGRAPH_EXPANSION_QUERY = """
MATCH (c:concept {name: $concept_name})
OPTIONAL MATCH (t:textual)-[:IS_A]->(c)
OPTIONAL MATCH (c)-[:INCLUDE_IN]->(h:hierarchy)
RETURN c.name       AS concept,
       collect(DISTINCT t.name) AS textual_facts,
       collect(DISTINCT h.name) AS hierarchy_parents
"""

# Batch update the Neo4j concept node.  We merge so reruns are idempotent.
UPSERT_DIFFICULTY_QUERY = """
UNWIND $rows AS row
MATCH (c:concept {name: row.concept})
SET c.centrality = row.centrality,
    c.difficulty  = row.difficulty
RETURN count(c) AS updated
"""