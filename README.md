<div align="center">

<h1>Scara Database Engine</h1>

<p>
  <strong>A database engine built from scratch in Python.</strong><br>
  Exploring how databases work from raw bytes on disk to query execution.
</p>

</div>

---

## About

Scara is a learning-focused database engine built from scratch in Python.

The goal is simple: **understand how a database actually works under the hood** by implementing its core components rather than treating it as a black box.

<div align="center">

<code>Python → Disk Storage → Storage Engine (Pages → Records → Tables) → SQL → Query Engine</code>

</div>

---

## Architecture

```text
┌─────────────────────────┐
│       User Interface    │
│        SQL / CLI        │
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│        SQL Layer        │
│ Tokenizer / Parser / AST│
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│       Query Engine      │
│   SELECT / INSERT / ... │
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│      Storage Engine     │
│ Tables / Records / Pages│
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│       Disk Storage      │
│          .db            │
└─────────────────────────┘
```

---

## Features

- Custom binary page format with slotted-page layout (fixed-size pages, variable-length records)
- Disk-based B-tree index, supporting both integer and string keys
- Hand-written tokenizer and recursive-descent parser for a SQL-like syntax
- Query engine that chooses between index lookup and full table scan depending on the query
- Typed schema layer — records are encoded/decoded between raw bytes and real Python values
- LRU-style caching for both pages and B-tree nodes
- CLI for direct interaction
- Streamlit web interface for a friendlier front end

---

## Setup

```bash
git clone https://github.com/Scaramballed/Database-engine.git
cd Database-engine
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Usage

**CLI:**

```bash
python engine/cli.py
```

**Streamlit interface:**

```bash
streamlit run engine/app.py
```

**Example session:**

```sql
> CREATE TABLE users (id int, name str)
> INSERT INTO users VALUES (1, "alice")
> SELECT * FROM users WHERE id = 1
(1, "alice")
```

*(adjust this block to match your actual supported syntax/output)*

---

## Documentation & Learning Log

This project is documented as I build it, not after the fact.

- [`docs/`](./docs) — a written walkthrough of each core module (`Page`, `PageManager`, `Table`, `Schema`, B-tree indexing) explaining not just what the code does, but why it's structured that way.
- [`LEARNING_LOG.md`](./LEARNING_LOG.md) — My progress of how I learned, especially as a begineer at programming, like a short diary.
---

## Status

Actively in progress. Current focus: DELETE support (B-tree deletion + keeping the table and index in sync).

---

## License

MIT — see [LICENSE](./LICENSE).
