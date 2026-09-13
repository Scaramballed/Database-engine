# Schema Layer

**The whole job of these lines of codes to contain helper functions to encode the tables into bytes and decode it into readable data.**

```python
class Schema:
    def __init__(self, columns):
        self.columns = columns
        self.fmt = self._build_format() 
```

Most lines are self-explanatory but the `self.fmt` takes in the format we will be building right below it.

```python
def _build_format(self):
    fmt = ">"
    for col in self.columns:
        col_type = col[1]
        if col_type == "int":
            fmt += "i"
        elif col_type == "str":
            size = col[2]
            fmt += f"{size}s"
        else:
            raise ValueError(f"Unknown column type: {col_type}")
    return fmt
```

First comes the endian, which I've already explained in [Pages](Pages.md). After that, for every column we grab exactly index 1, since that's where the column type lives. If it's an int, we add "i" to our format string; if it's a str, we grab the size from index 2 and add it as f"{size}s". If the type is neither, we raise a ValueError telling us the column type wasn't recognized. We then return the finished fmt string, which is what lets struct.pack/unpack handle a mix of fixed-size ints and variable-length strings in the same record. That's the cool part about it.

```python


def encode(self, values):
    packed_values = []
    for col, value in zip(self.columns, values):
        col_type = col[1]
        if col_type == "str":
            size = col[2]
            encoded = value.encode("utf-8")
            if len(encoded) > size:
                raise ValueError(f"'{value}' is too long for column '{col[0]}' (max {size} bytes)")
            encoded = encoded.ljust(size, b"\x00")
            packed_values.append(encoded)
        else:
            packed_values.append(value)

    return struct.pack(self.fmt, *packed_values)  
```

`encode()` takes a row of real Python values and turns them into the packed bytes struct.pack can write to disk. `zip(self.columns, values)` pairs up each column definition with its corresponding value, so we know both what the value is and what type it's supposed to be at the same time.

For int columns, there's nothing to do — an int is already exactly what struct.pack wants, so it just gets appended to packed_values as-is. The only real work happens for str columns: value.`encode("utf-8")` turns the Python string into raw bytes, then we check if it's too long for the fixed size that column reserved (size), raising a clear error if so instead of letting struct.pack fail with a cryptic message. If it fits, `ljust(size, b"\x00")` pads it out with zero bytes until it's exactly size bytes long — this matters because our format string (f"{size}s") expects every string in that column to always be exactly the same fixed length, no matter how short the actual word is.

Once every value is either an int or a properly-sized byte string, `struct.pack(self.fmt, *packed_values)` does the actual packing in one call, using the format `string _build_format()` built earlier.

```python
def decode(self, data):
    raw_values = struct.unpack(self.fmt, data)    
    result = {}
    for col, raw in zip(self.columns, raw_values):
        name, col_type = col[0], col[1]
        if col_type == "str":
            result[name] = raw.rstrip(b"\x00").decode("utf-8")
        else:
            result[name] = raw
    return result
```

Unlike `encode()`, this time we build a dict rather than a list, so `zip(self.columns, raw_values)` pairs each column definition with its corresponding raw value, and `name, col_type = col[0], col[1]` pulls out both the column's name and its type, the name matters here because the return value needs to be something like {"name": "alice", "age": 30}, not just a bare positional tuple, so a caller can look values up by column name instead of remembering index order.

For int columns, the raw value coming out of unpack is already a usable Python int, so it goes straight into result unchanged. For str columns, there's real work to undo: raw is a fixed-size byte string that was padded with b"\x00" bytes back in encode(), so rstrip(b"\x00") strips that trailing padding off, and .`decode("utf-8")` converts the remaining raw bytes back into an actual Python string. Same asymmetry as before, ints round-trip for free, strings need the padding/encoding handled explicitly on both ends.
