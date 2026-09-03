//! PageRank micro-service for the KAQG Centrality Engine.
//!
//! Reads an undirected edge list from stdin in JSON form:
//!   {"edges": [{"src": 1, "dst": 2}, {"src": 2, "dst": 1}, ...]}
//!
//! Emits a JSON PageRank vector on stdout:
//!   {"ranks": [{"id": 1, "score": 0.25}, ...]}
//!
//! The implementation is the textbook power-iteration form with
//! damping factor 0.85.  It is intentionally dependency-free so it can
//! run inside the existing tokio binary without adding new crates.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::{self, Read};
use std::io::Write;

#[derive(Serialize, Deserialize, Debug)]
struct EdgeList {
    edges: Vec<Edge>,
}

#[derive(Serialize, Deserialize, Debug)]
struct Edge {
    src: u64,
    dst: u64,
}

#[derive(Serialize, Debug)]
struct RankedNode {
    id: u64,
    score: f64,
}

#[derive(Serialize, Debug)]
struct RankOutput {
    ranks: Vec<RankedNode>,
}

const DAMPING: f64 = 0.85;
const ITERATIONS: usize = 100;
const TOLERANCE: f64 = 1.0e-6;

fn main() {
    let mut buffer = String::new();
    io::stdin()
        .read_to_string(&mut buffer)
        .expect("[pagerank] failed to read stdin");
    let parsed: EdgeList =
        serde_json::from_str(&buffer).expect("[pagerank] invalid JSON edge list");

    let mut adjacency: HashMap<u64, Vec<u64>> = HashMap::new();
    let mut nodes: Vec<u64> = Vec::new();
    for edge in parsed.edges {
        adjacency.entry(edge.src).or_insert_with(Vec::new).push(edge.dst);
        if !nodes.contains(&edge.src) {
            nodes.push(edge.src);
        }
        if !nodes.contains(&edge.dst) {
            nodes.push(edge.dst);
        }
    }

    let n = nodes.len() as f64;
    if n == 0.0 {
        let payload = RankOutput { ranks: Vec::new() };
        println!("{}", serde_json::to_string(&payload).unwrap());
        return;
    }

    let init = 1.0_f64 / n;
    let mut ranks: HashMap<u64, f64> = nodes.iter().map(|id| (*id, init)).collect();

    for _ in 0..ITERATIONS {
        let mut next: HashMap<u64, f64> = nodes.iter().map(|id| (*id, (1.0 - DAMPING) / n)).collect();

        for (&src, neighbours) in adjacency.iter() {
            let out = neighbours.len() as f64;
            if out == 0.0 {
                continue;
            }
            let share = DAMPING * ranks[&src] / out;
            for &dst in neighbours {
                *next.entry(dst).or_insert(0.0) += share;
            }
        }

        let mut diff = 0.0;
        for id in &nodes {
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

    let payload = RankOutput { ranks: ranked };
    let stdout = io::stdout();
    let mut handle = stdout.lock();
    let serialized = serde_json::to_string(&payload).unwrap();
    handle.write_all(serialized.as_bytes()).unwrap();
    handle.write_all(b"\n").unwrap();
}