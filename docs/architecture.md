# Architecture

## Target pipeline

```text
NASA NTRS + ASRS
        |
        v
Acquisition and validation
        |
        v
PDF/text/table/figure extraction
        |
        v
Chunking + metadata + document lineage
        |
        +-----------------------+
        |                       |
        v                       v
Dense embeddings          Sparse index
        |                       |
        +----------+------------+
                   v
          Hybrid retrieval
                   |
                   v
                Reranker
                   |
                   v
       Grounded answer generation
                   |
                   v
     Citations + figures + evaluation
```

## Design principle

Every generated claim must be traceable to retrieved source content. Retrieval quality will be evaluated independently from answer quality.
