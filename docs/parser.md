# Parser (the recursive descent)

## Select and Insert Statement

```python
class SelectStatement:
    def __init__(self, columns, table, where=None):
        self.columns = columns
        self.table = table
        self.where = where

    def __repr__(self):
        return f"SelectStatement(columns={self.columns}, table={self.table!r}, where={self.where})"


class InsertStatement:
    def __init__(self, table, values):
        self.table = table
        self.values = values

    def __repr__(self):
        return f"InsertStatement(table={self.table!r}, values={self.values})"
```

These are AST (Abstract Syntax Tree) node classes — they're not doing any work themselves, they're just structured containers that represent what a query means after the parser has read through raw text like `SELECT id, name FROM users WHERE id = 1` and figured out its pieces. This is the output of your parser and the input to your query engine — the parser's whole job is to turn a string into one of these objects, and the query engine's job is to take one of these objects and actually execute it.

SelectStatement holds three things: columns (which fields were asked for), table (which table to read from), and where (an optional filter condition, defaulting to None when the query has no WHERE clause at all — e.g. `SELECT * FROM users`). InsertStatement is simpler, just table and values, since an insert doesn't need a column list or a filter — you're providing a full row of data, not asking for a subset.

## Parser

Most of these are basic syntaxes so I would only give short explaination for these lines of code (unlike Btrees)

```python

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self):
        token = self.current()
        self.pos += 1
        return token

    def expect(self, type_, value=None):
        token = self.current()
        if token is None or token.type != type_ or (value is not None and token.value != value):
            raise ValueError(f"Expected {type_} {value}, got {token}")
        return self.advance()

    def parse_statement(self):
        token = self.current()
        if token is None:
            raise ValueError("Empty query")

        if token.type == "KEYWORD" and token.value == "SELECT":
            return self.parse_select()
        elif token.type == "KEYWORD" and token.value == "INSERT":
            return self.parse_insert()
        else:
            raise ValueError(f"Unknown statement type: {token}")

    def parse_select(self):
        self.expect("KEYWORD", "SELECT")

        columns = [self.expect("IDENTIFIER").value]
        while self.current() is not None and self.current().type == "PUNCTUATION" and self.current().value == ",":
            self.advance()
            columns.append(self.expect("IDENTIFIER").value)

        self.expect("KEYWORD", "FROM")
        table = self.expect("IDENTIFIER").value

        where = None
        if self.current() is not None and self.current().type == "KEYWORD" and self.current().value == "WHERE":
            self.advance()
            where = self.parse_condition()

        return SelectStatement(columns, table, where)

    def parse_condition(self):
        column_token = self.expect("IDENTIFIER")
        operator_token = self.expect("OPERATOR")
        value = self.parse_value()
        return (column_token.value, operator_token.value, value)

    def parse_insert(self):
        self.expect("KEYWORD", "INSERT")
        self.expect("KEYWORD", "INTO")
        table = self.expect("IDENTIFIER").value
        self.expect("KEYWORD", "VALUES")
        self.expect("PUNCTUATION", "(")

        values = [self.parse_value()]
        while self.current() is not None and self.current().type == "PUNCTUATION" and self.current().value == ",":
            self.advance()
            values.append(self.parse_value())

        self.expect("PUNCTUATION", ")")

        return InsertStatement(table, values)

    def parse_value(self):
        token = self.current()
        if token is None or token.type not in ("NUMBER", "STRING"):
            raise ValueError(f"Expected NUMBER or STRING, got {token}")
        self.advance()
        return token.value
```

I would give the explaination pieces by pieces, since these are not that logically taxing.

```python
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
```

Standard recursive-descent parser setup — holds the full token list from the tokenizer and a `pos` cursor tracking which token we're currently looking at.

python

```python
    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self):
        token = self.current()
        self.pos += 1
        return token
```

`current()` peeks at the token under the cursor without moving it, returning `None` if we've run past the end. `advance()` grabs the current token, moves the cursor forward one, and returns what it just consumed — the two core primitives every other method builds on.

python

```python
    def expect(self, type_, value=None):
        token = self.current()
        if token is None or token.type != type_ or (value is not None and token.value != value):
            raise ValueError(f"Expected {type_} {value}, got {token}")
        return self.advance()
```

`expect()` is "assert the current token matches what the grammar requires here, or fail with a useful error." It checks the token type always, and the exact value only if one was given (so `expect("IDENTIFIER")` accepts any identifier, while `expect("KEYWORD", "SELECT")` demands that specific keyword) — then consumes it via `advance()` if it matches.

python

```python
    def parse_statement(self):
        ...
```

The dispatcher — looks at the first token to decide whether this is a `SELECT` or `INSERT` query, then hands off to the matching method. Anything else is an unsupported query and raises immediately.

python

```python
    def parse_select(self):
        ...
```

Walks through the grammar of a SELECT statement step by step: consume `SELECT`, collect one or more comma-separated column names (the `while` loop handles `col1, col2, col3` by repeatedly checking for a comma and grabbing another identifier), consume `FROM` and the table name, then optionally parse a `WHERE` clause if one is present. Ends by packaging everything into a `SelectStatement`.

python

```python
    def parse_condition(self):
        column_token = self.expect("IDENTIFIER")
        operator_token = self.expect("OPERATOR")
        value = self.parse_value()
        return (column_token.value, operator_token.value, value)
```

Parses one simple condition — `column OPERATOR value`, like `id = 1` — and returns it as a plain tuple rather than its own class, since it's a small enough structure not to need one.

python

```python
    def parse_insert(self):
        ...
```

Same idea as `parse_select`, just matching INSERT's grammar: `INSERT INTO table VALUES (v1, v2, ...)`. The comma-loop logic for collecting `values` is identical in shape to the column-collecting loop in `parse_select` — same pattern, different token type being collected.

python

```python
    def parse_value(self):
        token = self.current()
        if token is None or token.type not in ("NUMBER", "STRING"):
            raise ValueError(f"Expected NUMBER or STRING, got {token}")
        self.advance()
        return token.value
```

Consumes a single literal value, accepting either a number or a string token, and returns its raw value — used both for condition values and INSERT values.
