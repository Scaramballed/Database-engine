from tokenizer import Token, Tokenizer


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


if __name__ == "__main__":
    queries = [
        "SELECT id, name FROM users WHERE id = 5",
        "SELECT id FROM users",
        'INSERT INTO users VALUES (1, "Scara")',
        'INSERT INTO users VALUES (2, "Siddhartha")',
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        tokens = Tokenizer(q).tokenize()
        result = Parser(tokens).parse_statement()
        print(result)