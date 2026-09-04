
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

<code>Python → Storage → Pages → Records → Tables → SQL → Query Engine</code>

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
