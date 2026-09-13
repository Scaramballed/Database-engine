# CLI (Command line interface)

Now, finally we can see everything what we did, just the step of wrapping everything up

```python
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
```

This is the interactive front end tying every layer of the project together into something a person can actually type into. It's a classic **REPL loop** (Read-Eval-Print Loop) — read one line of input, evaluate it, print the result, repeat forever until told to stop.

`while True` runs indefinitely; `input("sql> ").strip()` reads one line of text and trims whitespace, giving the prompt its `sql>` look. `if query.lower() in ("exit", "quit"): break` is the exit condition — `.lower()` means the user can type `EXIT`, `Exit`, or `exit` and it'll still match. `if not query: continue` skips straight back to the top of the loop on an empty line (just pressing Enter with nothing typed), rather than trying to process nothing as a query.

The real work happens in the `try` block, and it's worth noticing this line is the entire pipeline you've built, called in sequence: `Tokenizer(query).tokenize()` turns raw text into tokens, `Parser(tokens).parse_statement()` turns tokens into an AST node (`SelectStatement`/`InsertStatement`), and `engine.execute(statement)` actually runs it and returns a result — three completely independent classes, each built and tested on its own, chained together in three lines. This is the payoff of having kept them decoupled the whole way through.

`except Exception as e: print(f"Error: {e}")` catches literally anything that goes wrong at any stage.
