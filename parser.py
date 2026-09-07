from tokenizer import Token, Tokenizer


class SelectStatement:
    def __init__(self, columns, table, where=None):
        self.columns = columns
        self.table = table
        self.where = where

    def __repr__(self):
        return f"SelectStatement(columns={self.columns}, table={self.table!r}, where={self.where})"


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

        value_token = self.current()
        if value_token is None or value_token.type not in ("NUMBER", "STRING"):
            raise ValueError(f"Expected NUMBER or STRING, got {value_token}")
        self.advance()

        return (column_token.value, operator_token.value, value_token.value)


if __name__ == "__main__":
    queries = [
        "SELECT id, name FROM users WHERE id = 5",
        "SELECT id FROM users",
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        tokens = Tokenizer(q).tokenize()
        result = Parser(tokens).parse_select()
        print(result)