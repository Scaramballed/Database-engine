from engine.tokenizer import Tokenizer
from engine.parser import Parser
from engine.queryengine import QueryEngine


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
    from engine.Pages import PageManager
    from engine.record import Schema
    from engine.Table import Table

    pm = PageManager("lelouch.db")
    index_pm = PageManager("lelouch_id_index.db")
    schema = Schema([("id", "int"), ("name", "str", 20)])
    table = Table(pm, schema, index_page_manager=index_pm, index_column="id")

    engine = QueryEngine({"lelouch": table})
    run_cli(engine)