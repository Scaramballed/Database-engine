from tokenizer import Tokenizer
from parser import Parser
from queryengine import QueryEngine

def run_cli(engine):
    print("Mini SQL CLI — type 'exit' to quit")
    while True:
        query = input("sql> ").strip()
        if query.lower() in ("exit", "quit"):
            break
        if not query:
            continue

        try:
            tokens = Tokenizer(query).tokenize()
            statement = Parser(tokens).parse_statement()
            result = engine.execute(statement)
            print(result)
        except Exception as e:
            print(f"Error: {e}")
if __name__ == "__main__":
    from Pages import PageManager
    from record import Schema
    from Table import Table

    pm = PageManager("mydb.db")
    index_pm = PageManager("mydb_id_index.db")
    schema = Schema([("id", "int"), ("name", "str", 20)])
    table = Table(pm, schema, index_page_manager=index_pm, index_column="id")

    engine = QueryEngine({"users": table})
    run_cli(engine)