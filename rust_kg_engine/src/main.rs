use neo4rs::*;
use serde::{Deserialize, Serialize};
use std::env;
use std::io::{self, Read};
use std::path::Path;

#[derive(Serialize, Deserialize, Debug)]
struct Triple {
    head: String,
    head_type: String,
    relation: String,
    tail: String,
    tail_type: String,
}

#[derive(Serialize, Deserialize, Debug)]
struct KGPayload {
    triples: Vec<Triple>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();

    // MODE 1: PDF Text Extraction
    if args.len() >= 3 && args[1] == "--extract-pdf" {
        let pdf_path = &args[2];
        if !Path::new(pdf_path).exists() {
            eprintln!("[Rust OCR Engine] File not found: {}", pdf_path);
            std::process::exit(1);
        }

        println!("[Rust OCR Engine] Extracting text from PDF: {}...", pdf_path);
        match pdf_extract::extract_text(pdf_path) {
            Ok(extracted_text) => {
                // Print extracted text to stdout so Python can consume it
                print!("{}", extracted_text);
            }
            Err(e) => {
                eprintln!("[Rust OCR Engine] Failed to extract text: {}", e);
                std::process::exit(1);
            }        }
        return Ok(());
    }

    // MODE 2: Graph Ingestion into Neo4j
    let mut buffer = String::new();
    io::stdin().read_to_string(&mut buffer)?;

    let payload: KGPayload = serde_json::from_str(&buffer)
        .expect("[Rust Engine] Failed to parse JSON payload");

    let uri = env::var("NEO4J_URI").expect("NEO4J_URI missing");
    let user = env::var("NEO4J_USER").expect("NEO4J_USER missing");
    let password = env::var("NEO4J_PASSWORD").expect("NEO4J_PASSWORD missing");
    let db_name = env::var("NEO4J_DATABASE").unwrap_or_else(|_| "neo4j".to_string());

    println!("[Rust Engine] Connecting to Neo4j Cloud at {}...", uri);

    let config = ConfigBuilder::default()
        .uri(&uri)
        .user(&user)
        .password(&password)
        .db(db_name.as_str())
        .build()?;
    let graph = Graph::connect(config).await?;

    println!("[Rust Engine] Processing {} triples...", payload.triples.len());

    let mut txn = graph.start_txn().await?;

    for triple in payload.triples {
        let rel_type = triple.relation.to_uppercase();
        let cypher = format!(
            "MERGE (h:{head_label} {{name: $head}}) \
             MERGE (t:{tail_label} {{name: $tail}}) \
             MERGE (h)-[r:{rel}]->(t)",
            head_label = triple.head_type,
            tail_label = triple.tail_type,
            rel = rel_type
        );

        let query = query(&cypher)
            .param("head", triple.head)
            .param("tail", triple.tail);

        txn.run(query).await?;
    }

    txn.commit().await?;
    println!("[Rust Engine] Graph creation successful!");
    Ok(())
}