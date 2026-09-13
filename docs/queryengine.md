# Query Engine

This only contains a single class

```python
def __init__(self, tables):
    self.tables = tables
def execute(self, statement):
    if isinstance(statement, SelectStatement):
        return self._execute_select(statement)
    elif isinstance(statement, InsertStatement):
        return self._execute_insert(statement)
    else:
        raise ValueError(f"Unknown statement type: {statement}")
```

This is the query engine's dispatcher — the execution-side counterpart to `Parser.parse_statement()`. It takes whatever AST node the parser produced (a `SelectStatement` or `InsertStatement` object) and routes it to the method that actually knows how to carry it out.

`isinstance(statement, SelectStatement)` checks whether `statement` is an object of that specific class (or a subclass of it) — it's Python's built-in way of asking "what type of object is this, at runtime?" This matters here because `execute()` doesn't know ahead of time which kind of statement it's been handed; the parser could have produced either type, and this function has to figure out which one it actually got before deciding what to do with it. It's the same underlying idea as checking `token.type == "KEYWORD"` in the parser, just operating on whole objects instead of token type strings — "is this the right kind of thing for the branch I'm about to run?"

This is also the moment the two AST classes from earlier actually earn their existence: because `SelectStatement` and `InsertStatement` are distinct classes rather than, say, both being plain dicts or tuples, `isinstance` can tell them apart cleanly. If they'd been generic dicts instead, you'd have needed some other marker (like a `"type": "select"` key) to distinguish them — using real classes makes the distinction structural rather than something you have to remember to check for by hand.

## Now finally everything comes together

```python
def _execute_select(self, statement):
    table = self.tables[statement.table]

    if statement.where is not None:
        column, operator, value = statement.where
        if column == table.index_column and operator == "=":
            record = table.get_record_by_index(self._cast(value))
            records = [record] if record is not None else []
        else:
            records = self._scan_and_filter(table, statement.where)
    else:
        records = self._scan_all(table)

    return [self._project(r, statement.columns) for r in records]
```

This is the actual query-planning logic — the part of the engine that decides _how_ to satisfy a SELECT, not just _that_ it should. `self.tables[statement.table]` looks up the real `Table` object by name, since the AST only stored the table name as a plain string, not a reference to the actual object.

Then there's a three-way decision on how to gather records:

**No WHERE clause at all** — `_scan_all(table)` just returns every record in the table, since nothing needs filtering.

**WHERE clause exists, and it's checking equality on the indexed column** (`column == table.index_column and operator == "="`) — this is the fast path. Instead of reading every record in the table, it goes straight through `table.get_record_by_index()`, which uses the B-tree to jump directly to the matching row's location. This is the entire reason you built an index in the first place — this check is where that investment actually pays off. `self._cast(value)` presumably converts the raw parsed value (which came out of the tokenizer as a generic string/number) into whatever type the index actually expects to compare against (e.g. turning a string `"5"` into an int `5` if the index key type is `int`). Since a lookup by unique key returns at most one match, `records` becomes a one-item list if something was found, or empty if not — wrapped this way so the rest of the function can treat both the indexed and non-indexed paths identically as "a list of matching records."

**WHERE clause exists, but on a non-indexed column, or using an operator other than `=`** (like `>`, `<`, or filtering on a column with no index at all) — the B-tree can't help here, since it's only built to answer "find this exact key," not general filtering. So this falls back to `_scan_and_filter()`, which presumably reads every record and manually checks the condition against each one — slower, but the only option available when there's no index to exploit.

Finally, `[self._project(r, statement.columns) for r in records]` — regardless of which path found the records, this last step trims each full row down to only the columns the query actually asked for (`SELECT id, name` shouldn't return every column in the table, just those two), producing the final result set.

```python
def _execute_insert(self, statement):
    values = tuple(self._cast(v) for v in statement.values)
    table = self.tables[statement.table]
    return table.insert_record(values)
```

Much simpler than `_execute_select` since there's no query planning to do — insert has exactly one way to happen, not several strategies to choose between.

`self._cast(v) for v in statement.values` runs every value from the parsed INSERT through `_cast()` — the same casting helper used in `_execute_select()`. This matters because everything coming out of the parser is still in its raw, tokenizer-level form (numbers might still be strings, for instance), but `Table.insert_record()` — and ultimately `Schema.encode()` underneath it — expects real, correctly-typed Python values matching each column's declared type. This is the query engine's job specifically: bridging the gap between "text the user typed" and "typed values the storage layer can actually work with." `tuple(...)` wraps the whole generator expression into a tuple, matching whatever shape `insert_record()` expects its `values` argument to be in.

`self.tables[statement.table]` — same table lookup as in `_execute_select`, resolving the table name string from the AST into the actual `Table` object.

`return table.insert_record(values)` — hands the fully-typed values off to `Table`, which already knows how to encode them, find or allocate a page with room, write the record, update the index, and return the `(page_id, slot_id)` location, as covered in my `Table` docs. There's genuinely nothing new happening at this layer beyond casting and delegating — which is itself worth noting as a design point: the query engine doesn't duplicate any storage logic, it just translates a parsed statement into the right call on the right object.

```python
def _cast(self, value):
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return value
```

`_cast()` converts raw values coming out of the parser into usable Python types before they reach the storage layer. It's a rough, guess-based cast rather than a schema-aware one — it doesn't know which column a value is going into or what type that column was declared as; it only looks at what the value _looks like_.

`isinstance(value, str)` skips the check entirely if the value isn't a string already (e.g. it came through as an `int` from the tokenizer). `value.lstrip("-").isdigit()` strips a leading `-` off just for the check, then tests whether everything left is a digit — if so, the value is assumed to be a number and converted via `int(value)` (using the original string, so the negative sign is preserved in the conversion). Anything that doesn't pass this check — a genuine word like `"alice"`, or a string that isn't purely numeric — is returned unchanged.

**Known limitation:** since this has no visibility into the schema, it can't tell "a `str` column that happens to hold a numeric-looking value" apart from "an actual `int` column." A string like `"123"` intended for a `str` column would get silently converted to the int `123` here, which could then misbehave once it reaches `Schema.encode()`, since that column expects a byte-string shape, not an int. The correct fix would be casting against the column's actual declared type (from `table.schema.columns`) rather than inferring type from the text itself — noted here as a gap to revisit, not something currently handled.

```python
def _project(self, record, columns):
        return {col: record[col] for col in columns}
```

"Projection" is the standard relational-database term for this operation — taking a full row and keeping only a chosen subset of its columns. This is exactly what distinguishes `SELECT col1, col2 FROM ...` from `SELECT * FROM ...`.

`record` is a full row already decoded into a dict by `Schema.decode()` — something like `{"id": 1, "name": "alice", ...}` — holding every column the table has. `columns` is the list of column names the query actually requested, taken directly from `statement.columns` in the AST.

The dict comprehension walks through just the requested column names and pulls only those key-value pairs out of the full record, building a smaller dict containing exactly what was asked for. So if a table has five columns but the query only asked for two, this is the step that trims the other three off before the result is returned.

**Known limitation:** there's no check for a requested column name that doesn't actually exist on the record — `record[col]` would raise a raw `KeyError` for something like `SELECT nonexistent_column FROM users`, rather than a clearer, query-specific error message. Noted here as a gap to revisit, same category as other unhandled edge cases flagged elsewhere in the project.

```python
def _scan_all(self, table):
    records = []
    for page_id in table.page_ids:
        page = table.page_manager.read_page(page_id)
        for slot_id in range(page.num_slots):
            try:
                raw = page.get_record(slot_id)
                records.append(table.schema.decode(raw))
            except Exception:
                continue
    return records

def _scan_and_filter(self, table, where):
    column, operator, value = where
    value = self._cast(value)
    matches = []
    for record in self._scan_all(table):
        if self._compare(record[column], operator, value):
            matches.append(record)
    return matches

def _compare(self, left, operator, right):
    if operator == "=":
        return left == right
    elif operator == "<":
        return left < right
    elif operator == ">":
        return left > right
    else:
        raise ValueError(f"Unsupported operator: {operator}")
```

As for the `scan_all` function, it is the brute-force fallback — walks every page the table owns, every slot in each page, decodes whatever's there, and collects it. The try/except skips slots that raise (likely empty/deleted slots that don't hold a real record), rather than crashing the whole scan over one bad slot. This is the "no index available" path — cost scales directly with table size, unlike the indexed lookup in `_execute_select`.

Then, builds directly on `_scan_all()`  gets every record, then keeps only the ones satisfying the WHERE condition, checked one at a time via _compare(). value gets cast once up front rather than per-record, since the comparison value itself never changes across the loop.

And finally in the compare part, It just maps the three supported operator strings to their actual Python comparison, with a clear error for anything else the parser might have let through.
