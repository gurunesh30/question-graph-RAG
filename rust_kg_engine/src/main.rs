use neo4rs::*;
use serde::{Deserialize, Serialize};
use std::env;
use std::io::{self, Read};

#[derive(Serialize, Deserialize, Debug)]
struct Triple {
    head: String,
    head_type: String, // "hierarchy", "concept", "textual"
    relation: String,  // "part_of", "include_in", "is_a"
    tail: String,
    tail_type: String,
}

#[derive(Serialize, Deserialize, Debug)]
struct KGPayload {
    triples: Vec<Triple>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut buffer = String::new();
    io::stdin().read_to_string(&mut buffer)?;

    let payload: KGPayload = serde_json::from_str(&buffer)
        .expect("[Rust Engine] Failed to parse JSON payload");

    let uri = env::var("NEO4J_URI").expect("NEO4J_URI missing");
    let user = env::var("NEO4J_USER").expect("NEO4J_USER missing");
    let password = env::var("NEO4J_PASSWORD").expect("NEO4J_PASSWORD missing");

    println!("[Rust Engine] Connecting to Neo4j Cloud at {}...", uri);

    let config = ConfigBuilder::default()
        .uri(&uri)
        .user(&user)
        .password(&password)
        .build()?;

    let graph = Graph::connect(config).await?;

    println!("[Rust Engine] Processing {} triples...", payload.triples.len());

    // Execute queries inside an explicit transaction context
    let mut txn = graph.start_txn().await?;

    for triple in payload.triples {
        let cypher = format!(
            "MERGE (h:{head_label} {{name: $head}}) \
             MERGE (t:{tail_label} {{name: $tail}}) \
             MERGE (h)-[r:{rel}]->(t)",
            head_label = triple.head_type,
            tail_label = triple.tail_type,
            rel = triple.relation.to_uppercase()
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