//! `kaqg_ingest` binary.
//!
//! Two modes:
//!   * `--extract-pdf <PATH>`  -> stream extracted text to stdout.
//!   * (no args)               -> read JSON `KgPayload` from stdin and
//!                                write triples to Neo4j inside an
//!                                atomic transaction.

use std::env;
use std::io::{self, Read};
use std::path::Path;
use std::process::ExitCode;

use anyhow::{Context, Result};
use kaqg_core::{init_tracing, KgPayload, Triple};
use neo4rs::{ConfigBuilder, Graph};
use tracing::{error, info};

#[tokio::main]
async fn main() -> ExitCode {
    match run().await {
        Ok(()) => ExitCode::SUCCESS,
        Err(err) => {
            error!("{err:#}");
            ExitCode::from(1)
        }
    }
}

async fn run() -> Result<()> {
    init_tracing();
    let args: Vec<String> = env::args().collect();

    if args.len() >= 3 && args[1] == "--extract-pdf" {
        return run_pdf_mode(&args[2]);
    }
    run_neo4j_mode().await
}

fn run_pdf_mode(path: &str) -> Result<()> {
    if !Path::new(path).exists() {
        anyhow::bail!("file not found: {path}");
    }
    info!(path = %path, "extracting PDF text");
    let text = pdf_extract::extract_text(path)
        .with_context(|| format!("failed to extract text from {path}"))?;
    print!("{text}");
    Ok(())
}

async fn run_neo4j_mode() -> Result<()> {
    let mut buffer = String::new();
    io::stdin()
        .read_to_string(&mut buffer)
        .context("failed to read JSON payload from stdin")?;
    let payload: KgPayload = serde_json::from_str(&buffer)
        .context("invalid JSON payload")?;

    let uri = require_env("NEO4J_URI")?;
    let user = require_env("NEO4J_USER")?;
    let password = require_env("NEO4J_PASSWORD")?;
    let db = env::var("NEO4J_DATABASE").unwrap_or_else(|_| "neo4j".to_string());

    info!(%uri, database = %db, triples = payload.triples.len(), "connecting to Neo4j");
    let config = ConfigBuilder::default()
        .uri(&uri)
        .user(&user)
        .password(&password)
        .db(db.as_str())
        .build()
        .context("failed to build Neo4j config")?;
    let graph = Graph::connect(config).await.context("failed to connect to Neo4j")?;

    let mut txn = graph.start_txn().await.context("failed to start transaction")?;
    for triple in &payload.triples {
        run_triple(&mut txn, triple).await?;
    }
    txn.commit().await.context("failed to commit transaction")?;
    info!("graph creation successful");
    Ok(())
}

async fn run_triple(txn: &mut neo4rs::Txn, triple: &Triple) -> Result<()> {
    let rel = triple.relation.to_uppercase();
    let cypher = format!(
        "MERGE (h:{head} {{name: $head}}) \
         MERGE (t:{tail} {{name: $tail}}) \
         MERGE (h)-[r:{rel}]->(t)",
        head = triple.head_type,
        tail = triple.tail_type,
        rel = rel,
    );
    let q = neo4rs::query(&cypher)
        .param("head", triple.head.clone())
        .param("tail", triple.tail.clone());
    txn.run(q).await.context("failed to run Cypher MERGE")?;
    Ok(())
}

fn require_env(name: &str) -> Result<String> {
    env::var(name).with_context(|| format!("environment variable {name} is required"))
}
