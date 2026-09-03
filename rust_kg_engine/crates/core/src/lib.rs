//! Shared library for the KAQG Rust workspace.
//!
//! Houses the data types that the `kaqg_ingest` and `kaqg_pagerank`
//! binaries both need so they don't duplicate definitions.

use serde::{Deserialize, Serialize};

/// A single knowledge-graph triple produced by the LLM.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Triple {
    pub head: String,
    pub head_type: String,
    pub relation: String,
    pub tail: String,
    pub tail_type: String,
}

/// Top-level payload streamed to `kaqg_ingest` on stdin.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KgPayload {
    pub triples: Vec<Triple>,
}

/// PageRank input — an undirected (treated as directed for the random
/// walk) edge list keyed by integer ids.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Edge {
    pub src: u64,
    pub dst: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeList {
    pub edges: Vec<Edge>,
}

#[derive(Debug, Clone, Serialize)]
pub struct RankedNode {
    pub id: u64,
    pub score: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct RankOutput {
    pub ranks: Vec<RankedNode>,
}

/// Initialise a structured `tracing` subscriber once.
pub fn init_tracing() {
    let _ = tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .with_target(false)
        .try_init();
}
