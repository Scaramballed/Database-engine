KEYWORDS = {"SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "AND", "OR"}


class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


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


if __name__ == "__main__":
    queries = [
        "SELECT id, name FROM users WHERE id = 5",
        'INSERT INTO users VALUES (1, "Scara")',
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        tokens = Tokenizer(q).tokenize()
        for t in tokens:
            print(f"  {t}")