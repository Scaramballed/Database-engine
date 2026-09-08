from parser import SelectStatement, InsertStatement


class QueryEngine:
    def __init__(self, tables):
        self.tables = tables   # dict: table_name -> Table object

    def execute(self, statement):
        if isinstance(statement, SelectStatement):
            return self._execute_select(statement)
        elif isinstance(statement, InsertStatement):
            return self._execute_insert(statement)
        else:
            raise ValueError(f"Unknown statement type: {statement}")

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

    def _execute_insert(self, statement):
        values = tuple(self._cast(v) for v in statement.values)
        table = self.tables[statement.table]
        return table.insert_record(values)

    def _cast(self, value):
        if isinstance(value, str) and value.lstrip("-").isdigit():
            return int(value)
        return value

    def _project(self, record, columns):
        return {col: record[col] for col in columns}

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

#for the testing purposes hehe
if __name__ == "__main__":
    import os
    from Pages import PageManager
    from record import Schema
    from Table import Table
    from tokenizer import Tokenizer
    from parser import Parser

    for f in ("qe_test.db", "qe_test_index.db"):
        if os.path.exists(f):
            os.remove(f)

    pm = PageManager("qe_test.db")
    index_pm = PageManager("qe_test_index.db")
    schema = Schema([("id", "int"), ("name", "str", 20)])
    table = Table(pm, schema, index_page_manager=index_pm, index_column="id")

    engine = QueryEngine({"users": table})

    queries = [
        'INSERT INTO users VALUES (1, "Scara")',
        'INSERT INTO users VALUES (2, "Siddhartha")',
        'INSERT INTO users VALUES (3, "Bhusal")',
        "SELECT id, name FROM users WHERE id = 2",
        "SELECT name FROM users WHERE name = \"Bhusal\"",
        "SELECT id, name FROM users",
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        tokens = Tokenizer(q).tokenize()
        statement = Parser(tokens).parse_statement()
        result = engine.execute(statement)
        print(result)