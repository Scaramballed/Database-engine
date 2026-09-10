# Pages

This particular file consists of 2 classes, the Page and the Page Manager, the reason I did not include the 'table' class was due to the fact, it does not really touch the bytes in the disk like Pages or Schema (which I will cover later) does.

## Page

The sole reason of this class is to create the page format, the header, the freespace and finally the records. Some pages have been dedicated to metadata or indexing which again, I will be covering later on.

```python
HEADER_FORMAT = "<HH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
SLOT_FORMAT = "<HH"
SLOT_SIZE = struct.calcsize(SLOT_FORMAT)
```

Before I talk about this, I highly suggest that you first learn what formatting is in general.

The `<` is the byte-order indicator (endianness). It tells `struct` to use **little-endian** byte order, meaning that the least significant byte is stored first when a multi-byte value is represented in memory or written to disk.

I won't be explaining endianness in this much detail every time, but it is important to understand what it means before continuing.

The `H` represents an **unsigned short integer**, which occupies 2 bytes when using the standard sizes defined by `struct`.

Therefore, `<HH` consists of two `H` values:

- `H` → 2 bytes
- `H` → 2 bytes
- Total → 4 bytes

As you can see in the second line, I also calculate the size of the format using `struct.calcsize()`. This gives us a fixed size for our header and slot structures.

The header contains two values: `num_slots` and `free_space_offset`.

The slot contains two values: the `offset` and `length` of a record.

Having a fixed size for these structures is important because it allows us to know exactly where each header or slot begins and ends inside the page.

```python
class Page:
    def __init__(self):
        self.buffer = bytearray(PAGE_SIZE)
        self.num_slots = 0
        self.free_space_offset = PAGE_SIZE
        self._write_header()
```

