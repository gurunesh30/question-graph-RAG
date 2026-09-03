//! `kaqg_pagerank` micro-service.
//!
//! Reads a JSON `EdgeList` from stdin, runs textbook power-iteration
//! PageRank with damping 0.85, and writes a `RankOutput` to stdout.
//! Intentionally dependency-free of graph frameworks so the binary
//! stays small and fast.

use std::collections::{HashMap, HashSet};
use std::io::{self, Read, Write};
use std::process::ExitCode;

use anyhow::{Context, Result};
use kaqg_core::{init_tracing, EdgeList, RankOutput, RankedNode};

const DAMPING: f64 = 0.85;
const ITERATIONS: usize = 100;
const TOLERANCE: f64 = 1.0e-6;

fn run() -> Result<()> {
    init_tracing();
    let mut buffer = String::new();
    io::stdin()
        .read_to_string(&mut buffer)
        .context("failed to read stdin")?;
    let parsed: EdgeList = serde_json::from_str(&buffer).context("invalid edge list")?;

    let (adjacency, nodes) = build_graph(&parsed);
    let ranks = if nodes.is_empty() {
        Vec::new()
    } else {
        power_iterate(&adjacency, &nodes)
    };

    let payload = RankOutput { ranks };
    let stdout = io::stdout();
    let mut handle = stdout.lock();
    serde_json::to_writer(&mut handle, &payload).context("failed to write JSON")?;
    handle.write_all(b"\n").context("failed to write newline")?;
    Ok(())
}

fn build_graph(parsed: &EdgeList) -> (HashMap<u64, Vec<u64>>, Vec<u64>) {
    let mut adjacency: HashMap<u64, Vec<u64>> = HashMap::new();
    let mut seen: HashSet<u64> = HashSet::new();
    let mut order: Vec<u64> = Vec::new();
    for edge in &parsed.edges {
        if seen.insert(edge.src) {
            order.push(edge.src);
        }
        if seen.insert(edge.dst) {
            order.push(edge.dst);
        }
        adjacency.entry(edge.src).or_default().push(edge.dst);
    }
    (adjacency, order)
}

fn power_iterate(adjacency: &HashMap<u64, Vec<u64>>, nodes: &[u64]) -> Vec<RankedNode> {
    let n = nodes.len() as f64;
    let init = 1.0 / n;
    let mut ranks: HashMap<u64, f64> = nodes.iter().map(|id| (*id, init)).collect();

    for _ in 0..ITERATIONS {
        let mut next: HashMap<u64, f64> =
            nodes.iter().map(|id| (*id, (1.0 - DAMPING) / n)).collect();
        for (src, neighbours) in adjacency {
            let out = neighbours.len() as f64;
            if out == 0.0 {
                continue;
            }
            let share = DAMPING * ranks[src] / out;
            for dst in neighbours {
                *next.entry(*dst).or_insert(0.0) += share;
            }
        }
        let mut diff = 0.0;
        for id in nodes {
            diff += (next[id] - ranks[id]).abs();
        }
        ranks = next;
        if diff < TOLERANCE {
            break;
        }
    }

    let mut ranked: Vec<RankedNode> = ranks
        .into_iter()
        .map(|(id, score)| RankedNode { id, score })
        .collect();
    ranked.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
    ranked
}

fn main() -> ExitCode {
    if let Err(err) = run() {
        eprintln!("[kaqg_pagerank] error: {err:#}");
        return ExitCode::from(1);
    }
    ExitCode::SUCCESS
}
