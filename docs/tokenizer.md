# Tokenizer

Breaks the raw string into a flat list of meaningful chunks ("tokens"), throwing away irrelevant whitespace:

```text
SELECT id, name FROM users WHERE id = 5
```

becomes something like:

```text
[KEYWORD(SELECT), IDENT(id), COMMA, IDENT(name), KEYWORD(FROM), IDENT(users), KEYWORD(WHERE), IDENT(id), OP(=), NUMBER(5)]
```

This is a linear scan with some lookahead.

## Token

```python
class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"
```

Here you might have encountered `__repr__`. I also did not know what it was before so I would like to elaborate a bit on that part especially for the beginners.
`__repr__` is purely a **formatting method** — it defines what text gets produced when something (`print()`, a REPL) asks to display an object. It does not run automatically on its own and does not affect program behavior at all; deleting it changes nothing except how the object looks when printed. It exists here specifically because parser/tokenizer output benefits from being eyeballed while testing — unlike `Page` or `BTreeNode`, which were verified by checking specific fields or raw bytes directly instead.

I think other than that is self-explanatory.

## tokenizer

```python
class Tokenizer:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def tokenize(self):
        tokens = []
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char.isspace():
                self.pos += 1
                continue
            if char.isalpha():
                word = ""
                while self.pos < len(self.text) and self.text[self.pos].isalpha():
                    word += self.text[self.pos]
                    self.pos += 1
                if word.upper() in KEYWORDS:
                    tokens.append(Token("KEYWORD", word.upper()))
                else:
                    tokens.append(Token("IDENTIFIER", word))
                continue
            if char.isdigit():
                number = ""
                while self.pos < len(self.text) and self.text[self.pos].isdigit():
                    number += self.text[self.pos]
                    self.pos += 1
                tokens.append(Token("NUMBER", number))
                continue
            if char in ('"', "'"):
                quote_char = char
                self.pos += 1
                value = ""
                while self.pos < len(self.text) and self.text[self.pos] != quote_char:
                    value += self.text[self.pos]
                    self.pos += 1
                self.pos += 1
                tokens.append(Token("STRING", value))
                continue
            if char in ('=', '<', '>'):
                tokens.append(Token("OPERATOR", char))
                self.pos += 1
                continue
            if char in (',', '(', ')'):
                tokens.append(Token("PUNCTUATION", char))
                self.pos += 1
                continue
            raise ValueError(f"Unexpected character: {char!r} at position {self.pos}")
        return tokens
```

```python
if word.upper() in KEYWORDS:
    token = ("KEYWORD", word.upper())
else:
    token = ("IDENTIFIER", word)
```

This is _why_ keywords are "reserved" in every real SQL implementation — a column literally named `WHERE` would always tokenize as `KEYWORD`, never `IDENTIFIER`, since the lookup can't distinguish intent.

**The cursor (`self.pos`):** a manually-advanced index into the string, not a `for char in text` loop — needed because some tokens span multiple characters, and a plain for-loop hands you the next character automatically whether the current chunk is finished or not. `self.pos` lets inner loops consume as many characters as a token actually needs before returning control to the outer loop.

After that the helper functions are mostly similar. Every branch follows the same idea: **keep consuming characters while some condition holds, then tag the finished chunk.** Only the stopping condition changes (still a letter? still a digit? not the closing quote?) — the surrounding structure is identical every time.

**Letters vs. keywords — the key insight:** the tokenizer scans letters identically regardless of what word it turns out to be. It has no special-casing for `WHERE` vs `id` while scanning.
