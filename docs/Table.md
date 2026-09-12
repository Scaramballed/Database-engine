# TABLE

This is something that took me a lot of perservarance, since most of the things like indexes, schema are wired here. So it is very important to deeply understand these particular lines of codes.
As you might be aware, but table's job is to write metadata, load metadata, insert records, get the records, and wire the Btree with pages.

```python
META_PAGE_ID = 0
```

Here we make sure we claim the first page soely for metadata, just a design choice and convention. Better to have all offsets in the first page.

```python
class Table:
    def __init__(self, page_manager, schema, index_page_manager=None, index_column=None):   
        self.page_manager = page_manager
        self.schema = schema
        self.page_ids = []

        if self.page_manager.is_new():
            self._write_metadata() 
        else:
            self._load_metadata()

        self.index = None
        self.index_column = index_column
        if index_page_manager is not None:
            index_col_type = next(col[1] for col in schema.columns if col[0] == index_column)  
            key_type = "string" if index_col_type == "str" else "int"                            
            self.index = BTreeIndex(index_page_manager, key_type=key_type)                  
```

This is the part where seperate pieces Table, PageManager, Schema, and BTreeIndex all have to agree with each other.

Table takes `page_manager` and a `schema` as arguments. This is because it doesn't know or care how to open or how a Pagemanager manages its cache internally, so it needs something that can read and write pages for it. And yeah same with schema (I have covered this on a separate page)

`self.page_ids[]`, this is the in memory list of which pages currently belong to this particular table. Table needs to keep track of which page_ids are its own so it knows where to look when scanning or inserting. Also, it always starts empty and only is populated by `_write_metadata()` or `_load_metadata()`.

And if the page manager is new we write the metadata, cause when the file is fresh there is no metadata sitting, and similarly when it does exists we just load it.

Now the indexing now, an index is optional so we gate it behind `index_page_manager is not None`. So if there is no index there we just do full scan (covered later).

Also the page manager for index should be different as you might have noticed, this is mainly because if we have same page manager the page IDs for table rows and page IDs for Btree node would collide in the same numbering space and the same cache.

After that we have the line `index_col_type = next(col[1] for col in schema.columns if col[0] == index_column)`
This line is figuring out what type of data the column being indexed actually holds, by looking it up in the schema. schema.columns is a list of tuples (covered later) like ("name", "str") or ("id", "int"), so col[0] is the column name and col[1] is its type. The generator expression (col[1] for col in schema.columns if col[0] == index_column) filters down to just the column matching index_column and pulls out its type; wrapping it in next() grabs the first (and only) match. If no column matches index_column, this raises StopIteration.

After that you might notice that we are translating from str to string. Why bother doing this translation at all, instead of just passing index_col_type straight through? Because Schema and BTreeIndex speak slightly different vocabularies for the same concept — Schema calls it "str" , while BTreeIndex calls it "string". Its merely a design choice, you can choose to calls string or str in both Btree and Schema. It is just I forgot about this so rather than changing everything. Just tweaking few lines can solve this problem.

```python
def _write_metadata(self):
    count = len(self.page_ids)
    data = struct.pack(f"<I{count}I", count, *self.page_ids)
    padded = data.ljust(PAGE_SIZE, b"\x00")
    self.page_manager.write_raw(META_PAGE_ID, padded)

def _load_metadata(self):
    raw = self.page_manager.read_raw(META_PAGE_ID)
    count = struct.unpack_from("<I", raw, 0)[0]
    self.page_ids = list(struct.unpack_from(f"<{count}I", raw, 4)) if count else []
```

As we talked about before, how writing and loading is different. In metedata, we store information about the page itself, its id.

`_write_metadata` is actually what persists the ids to the disk, since without this, this list living in the memory would vanish the moment the program exits, and next time there is no way to know which pages belonged to it.
So first we count the number of ids. After that the format string `f"<I{count}I"` comes in play, if there are 5 pages meaning, one unsigned int (I, 4 bytes) for count itself, followed by count more unsigned ints, one per page ID. And then we call to pack it, here you might have noticed the use of '*' , that unpacks the page_ids list so each ID becomes its own positional argument matching one of the Is in the format string.

Why store count at all, when in theory you could just read page_ids until you run out of bytes? Because a page is a fixed PAGE_SIZE block, you can't tell just by looking at the raw bytes where the real data ends and the leftover zero-padding begins. Storing the count up front means `_load_metadata()` knows exactly how many integers to read back out, and can safely ignore everything after that.

Then we pad it with null bytes, since the page size is fixed, it guarantees the metadata page is exactly `PAGE_SIZE` bytes, clean and predictable.

Other than that it is mostly similar. But I would like to emphasize a line of code.
`count = struct.unpack_from("<I", raw, 0)[0]` reads just the first 4 bytes as a single unsigned int — this is count, sitting at offset 0 because that's exactly where _write_metadata() put it. unpack_from returns a tuple even when unpacking a single value, which is why there's a [0] at the end to pull the bare integer out of (count,), and `struct.unpack_from(f"<{count}I", raw, 4)` then reads count more unsigned ints, starting at offset 4 — skipping past the 4 bytes count itself occupied. Just like in `_write_metadata()`, the format string is built dynamically (f"<{count}I") because we don't know how many page IDs there are until we've read count off disk first — this is a two-step read for exactly that reason: you can't build the format string to read the page IDs until you know how many there are, and you can't know how many there are until you've read the first 4 bytes.

```python
def insert_record(self, values):
    record_bytes = self.schema.encode(values)

    if self.page_ids:
        last_page_id = self.page_ids[-1]
        page = self.page_manager.read_page(last_page_id)

        if page.free_space() >= len(record_bytes) + SLOT_SIZE:
            slot_id = page.insert_record(record_bytes)
            self.page_manager.write_page(last_page_id, page)
            self._update_index(values, last_page_id, slot_id)  
            return (last_page_id, slot_id)

    new_page_id = self.page_manager.allocate_page()
    new_page = Page()
    slot_id = new_page.insert_record(record_bytes)
    self.page_manager.write_page(new_page_id, new_page)
    self.page_ids.append(new_page_id)
    self._write_metadata()   

    self._update_index(values, new_page_id, slot_id)  
    return (new_page_id, slot_id)
```

To insert a record, first we have to convert the record into bytes which is done by schema layer. The page where we will be inserting a new record is the last page. And if there is enough free space in that page. And we assign the new record its slot id as well. Furthermore, we update its index so it does not cause any issue with Btree. But all of this happens if there is enough space, if not we allocate a new page, its id, and repeat, while also updating the metadata and the index. These are pretty simple lines of codes.

Simplification: only ever appends to the last page, so space freed by deletes in earlier pages is never reclaimed — fine for now, would need a free-space map or a page rescan to fix later. No rollback if index update fails after the page write — row and index could go out of sync.

```python
def get_record(self, page_id, slot_id):
    page = self.page_manager.read_page(page_id)
    raw = page.get_record(slot_id)
    return self.schema.decode(raw)

def _update_index(self, values, page_id, slot_id):
    if self.index is None:
        return
    column_names = [col[0] for col in self.schema.columns]
    key = values[column_names.index(self.index_column)]
    self.index.insert(key, page_id, slot_id)

def get_record_by_index(self, key):
    if self.index is None:
        raise ValueError("This table has no index configured")
    location = self.index.search(key)
    if location is None:
        return None
    page_id, slot_id = location
    return self.get_record(page_id, slot_id)
```

`get_record` is pretty straightforward, read the page, pull the raw bytes out, hand them to the decoding part to get real values back.

`get_record_by_index()` is also mostly self-explanatory, guard against no index configured, ask the index to search, unpack the (page_id, slot_id) tuple it returns, then reuse `get_record()` to actually fetch the row.

few lines worth looking at, `column_names` and `key`
This is solving a specific mismatch: values (the row being inserted) is a plain list/tuple of raw values with no field names attached — it's positional, like ["alice", 30]. But self.index_column is a name, like "name". So to pull the right value out of values, you first need to know which position that column lives at. column_names = [col[0] for col in self.schema.columns] rebuilds the ordered list of column names from the schema (e.g. ["name", "age"]), and column_names.index(self.index_column) finds where "name" sits in that list — say, index 0. Then values[0] is the actual value to index on. It's essentially converting a name-based lookup into a position-based one, using the schema as the map between the two.
