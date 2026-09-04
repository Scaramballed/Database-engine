import struct

class Schema:
    def __init__(self, columns):
        self.columns = columns
        self.fmt = self._build_format() 

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