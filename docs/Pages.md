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

Here, we initialize a new `Page` instance and set up the initial state of the page.

`self` refers to the particular `Page` object currently being initialized. This allows us to store attributes such as `buffer`, `num_slots`, and `free_space_offset` on that specific instance.

First, we create `self.buffer` as a `bytearray` with a size of `PAGE_SIZE`. This gives the page a fixed-size, mutable block of memory in which its bytes can be stored and manipulated.

Next, `self.num_slots` is initialized to `0` because the page does not contain any records yet, and therefore has no slots.

`self.free_space_offset` is initially set to `PAGE_SIZE`. Since the page is empty, the free space begins at the end of the page. As records are added, this offset will move toward the beginning of the page to indicate where the free space currently ends.

Finally, `_write_header()` is called to write the page's initial metadata into the buffer.

```python
def _write_header(self):
        struct.pack_into(HEADER_FORMAT, self.buffer, 0, self.num_slots, self.free_space_offset)
def _slot_offset(self, slot_index):
    return HEADER_SIZE + slot_index * SLOT_SIZE
def free_space(self):
    slot_array_end = HEADER_SIZE + self.num_slots * SLOT_SIZE
    return self.free_space_offset - slot_array_end
```

Here we have a few helper functions for managing the page. _write_header() basically takes the current values of num_slots and free_space_offset and writes them into the beginning of the buffer according to our HEADER_FORMAT. _slot_offset() is just calculating where a particular slot starts in the slot array. Since the header comes first, we start at HEADER_SIZE and then move forward by SLOT_SIZE for every slot.  
Finally, free_space() calculates how much actual free space is left on the page. The slot array ends at HEADER_SIZE + num_slots * SLOT_SIZE, while the records/data start from free_space_offset and grow backwards. So subtracting the end of the slot array from free_space_offset gives us the space between the two regions, which is the currently available free space.

```python
    def insert_record(self, record):
        record_size = len(record)
        if self.free_space()<record_size + SLOT_SIZE:
            raise Exception("Not enough space to insert record")
        self.free_space_offset -=record_size
        self.buffer[self.free_space_offset:self.free_space_offset +record_size] = record
        slot_id = self.num_slots
        struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id), self.free_space_offset, record_size)
        self.num_slots +=1
        self._write_header()
        return slot_id
```

I would like to elaborate a bit more on this particular helper function, in case it causes any confusion. The first few lines are pretty self-explanatory. We first check whether we have enough free space for both the record itself and its slot entry. If we don't, we raise an exception, and the higher-level logic can then handle putting the record into another page. If there is enough space, we subtract the record size from free_space_offset. Since our records grow backwards from the end of the page, this moves the offset towards the beginning of the page by exactly the amount of space required for the record.
We then use this new offset to place the actual record bytes into the buffer. After that, we assign a slot_id based on the current number of slots and use struct.pack_into() to write the record's offset and size into the corresponding slot entry. We use pack_into() because it allows us to pack the binary data directly into our existing bytearray buffer at a particular location, rather than creating a separate bytes object like struct.pack() would. Its signature is struct.pack_into(format, buffer, offset, v1, v2, ...), so in our case it writes the information about where the record is located and how large it is directly into the slot array.
Finally, we increase the number of slots, rewrite the header using the helper function we defined earlier, and return the slot_id so that we know where this record is located.

```python
def get_record(self, slot_id):
        offset, length = struct.unpack_from(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id)) 
        if length == 0:
            raise Exception("Record has been deleted")
        return bytes(self.buffer[offset:offset + length])
def delete_record(self, slot_id):
    offset, _ = struct.unpack_from(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id))
    struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id), offset, 0)
```

Before we get the record, we first need to read the information stored in its slot. Since the slot contains binary data, we use struct.unpack_from() with the same SLOT_FORMAT we used when inserting the record. This gives us two values: the offset, which tells us where the actual record starts in the page, and the length, which tells us how many bytes belong to that record. We use tuple unpacking here to directly assign those two values. The _slot_offset(slot_id) gives us the location of the slot entry itself, rather than the location of the record.
If length == 0, we know that the record has been deleted, since in our implementation we mark a deleted slot by setting its length to 0. Otherwise, we use the offset and length to slice the relevant bytes from the buffer and return them as a bytes object.
For delete_record(), we again first unpack the slot to get the record's offset. We don't actually need the length here, so we use '_' as a temporary variable for it. We then use struct.pack_into() to overwrite that slot with the same offset, but with its length set to 0. This means the record is now marked as deleted without actually removing its bytes from the page. Later, the storage engine can potentially reuse that space.

```python
def update_record(self, slot_id, new_bytes):
    old_offset, old_length = struct.unpack_from(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id))

    if len(new_bytes) <= old_length:
        # fits in the old space — overwrite in place, keep old_length in the slot
        self.buffer[old_offset:old_offset + len(new_bytes)] = new_bytes
        struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id), old_offset, len(new_bytes))
    else:
        # since it doesnt fit we just kinda point it to a new location in the free space, and update the slot to point to that new location. The old space is now wasted, but we can reclaim it later when we compact the page.
        if self.free_space() < len(new_bytes):
            raise ValueError("Page full")
        self.free_space_offset -= len(new_bytes)
        self.buffer[self.free_space_offset:self.free_space_offset + len(new_bytes)] = new_bytes
        struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id), self.free_space_offset, len(new_bytes))
        self._write_header()
def to_bytes(self):
    return bytes(self.buffer)
```

Here, we first unpack the previous offset and length of the record as `old_offset` and `old_length`, since we need to know where the existing record is and how much space it currently occupies.

The `if` statement checks whether the new record can fit into the space previously occupied by the old record. If `len(new_bytes) <= old_length`, we can simply overwrite the old record in place. We then update the slot with the new length while keeping the same offset.

If the new record is larger than the old one, it no longer fits in its previous space. In that case, we check whether there is enough free space elsewhere in the page. If there is, we move the new record to a new location at the end of the free space and update the slot so that it now points to this new location. The old space is left unused for now, creating wasted space inside the page, which can potentially be reclaimed later when we implement page compaction.

As for `to_bytes()`, this helper simply converts our page's `bytearray` buffer into a `bytes` object. The main reason for having this helper is just convenience and readability, so whenever we see `to_bytes()`, it is immediately clear that we are getting the page's contents as immutable bytes.

```python
    @classmethod
    def from_bytes(cls, data):
        page = cls.__new__(cls)
        page.buffer = bytearray(data)
        page.num_slots, page.free_space_offset = struct.unpack_from(HEADER_FORMAT, page.buffer, 0)
        return page
```

Here, we are basically doing the reverse of what we did before with `to_bytes()`. Instead of taking our page and converting it into bytes, we take the bytes and reconstruct a Page object from them. We first create a new instance using `cls.__new__(cls)`, which allows us to create the object without running the normal `__init__()` method, since we don't want to initialize a completely new empty page—we want to reconstruct the page from the data we already have. We then convert the data into a bytearray so that the buffer remains mutable, and finally unpack the header from the beginning of the buffer to recover the num_slots and free_space_offset values. We then return this reconstructed page.

## PageManager

In the page manager class, as you might have guessed it, yes it manages pages. That could be things like writing a page, reading the page, allocate a page, and also caching. We also wire pagemanager with our indexing, which we have done using Btree, and its caching as well. So a lot is happening here and it is very important to understand this

```python
 def __init__(self, filename, poolsize=64):
        try:
            self.file = open(filename, "r+b")
        except FileNotFoundError:
            open(filename, "wb").close() 
            self.file = open(filename, "r+b")
        self.cache = OrderedDict() # caching lesss gooo
        self.pool_size = poolsize
        self.node_cache = OrderedDict()   
```

As for this, there are a few things to take note of. We first try to open the file using `"r+b"`, which means read and write in binary mode. The important thing here is that it allows us to both read from and write to the existing database file without overwriting its contents. If the file does not exist, we catch the `FileNotFoundError` and create a new empty file using `"wb"`. We immediately close it because we only needed `"wb"` to create the file; we don't actually need to write anything to it at this point. We then open the newly created file again using `"r+b"`, so it is now ready for both reading and writing.

For the cache, we use an `OrderedDict`, since it keeps track of the order of the entries. This makes it much easier to implement an LRU (Least Recently Used) cache, where we can keep track of which page was used most recently and remove the least recently used one when the cache becomes full. We have another `OrderedDict` for `node_cache`, which works on the same idea but will be used for caching nodes that we need for indexing.

```python
    def allocate_page(self):
        self.file.seek(0, 2)
        file_size = self.file.tell()
        return file_size // PAGE_SIZE

    def write_page(self, page_id, page):
        offset = page_id * PAGE_SIZE
        self.file.seek(offset)
        self.file.write(page.to_bytes())

        self.cache[page_id] = page # keep cache in sync with what's now on disk
        self.cache.move_to_end(page_id)  
        self._evict_if_needed()
```

`allocate_page()` basically figures out what the next page ID should be. We move to the end of the file using `seek(0, 2)` and then use `tell()` to get the current file size. Since every page has a fixed size of `PAGE_SIZE`, dividing the file size by `PAGE_SIZE` gives us the ID of the next page that can be allocated.

For `write_page()`, we calculate the exact position of the page in the file using `page_id * PAGE_SIZE`, move to that position, and write the page's bytes to disk. After writing it, we also update the cache with the new version of the page and move that page to the end of the `OrderedDict`, since it has just been used. Finally, `_evict_if_needed()` makes sure the cache doesn't exceed its maximum size.

``since we are making sense of most of the codes now, I will skim the obvious stuffs ahead and give only the necessary explanations``

```python
def read_page(self, page_id):
    if page_id in self.cache:
        self.cache.move_to_end(page_id)
        return self.cache[page_id]
    print(f"cache miss for page {page_id}, reading from disk")
    offset = page_id * PAGE_SIZE
    self.file.seek(offset)
    data = self.file.read(PAGE_SIZE)
    page = Page.from_bytes(data)

    self.cache[page_id] = page   # js syncing it overall
    self._evict_if_needed()
    return page
```

When we have to read a page, we first check whether that `page_id` is already present in the cache. If it is, we move that `page_id` to the end of the `OrderedDict`, since it has just been accessed and is now the most recently used page, and then return the cached `Page` object. If it isn't there, we have a cache miss, so we have to actually read the page from disk.

We calculate the page's offset using its `page_id` and `PAGE_SIZE`, seek to that position in the file, and read `PAGE_SIZE` bytes. We then reconstruct the `Page` object from those bytes using `Page.from_bytes()`. Since we had to go to disk for this page anyway, we add it to the cache so that future reads can use the cached version instead. We then run the eviction helper to make sure the cache hasn't exceeded its allowed size, and finally return the page.

```python
def is_new(self):
    self.file.seek(0, 2)
    return self.file.tell() == 0
```

`is_new()` checks whether the file is completely empty. THe seek line check if the resulting postion is 0, and if it is, then we need a new file. This does not allocate though, just checking whether it is new or not.

```python
def write_raw(self, page_id, data: bytes):
    offset = page_id * PAGE_SIZE
    self.file.seek(offset)
    self.file.write(data)

def read_raw(self, page_id):
    offset = page_id * PAGE_SIZE
    self.file.seek(offset)
    return self.file.read(PAGE_SIZE)
```

The reason we do the write raw and read raw, they compute the offset the same way and write or read PAGE_SIZE bytes directly, but they do not care know or care about PAGE objects, so they don't touch cache at all. Everythin living on disk in fixed-size slots is a PAGE. So write_raw and read_raw gives us a way to move bytes to and from disk without assuming anything about what is inside them, and the caller decides how to interpret the bytes afterwards.

```python
def close(self):
    self.file.close()
def _evict_if_needed(self):
    if len(self.cache) > self.pool_size:
        oldest_id, oldest_page = self.cache.popitem(last=False)
```

Nothing fancy happening here. But as you can see in the evition, it makes sure that if the cache exceeds the pool size, it is evicted. This happens from the .popitem (last = False). Aso makes sure exactly that entry is removed.

```python
def read_node(self, page_id, key_type="int"):   
    if page_id in self.node_cache:
        self.node_cache.move_to_end(page_id)
        return self.node_cache[page_id]

    print(f"node cache miss for page {page_id}, reading from disk")
    raw = self.read_raw(page_id)
    node = BTreeNode.from_bytes(raw, key_type=key_type) 
    self.node_cache[page_id] = node
    self._evict_node_if_needed()
    return node

def write_node(self, page_id, node):
    self.write_raw(page_id, node.to_bytes())

    self.node_cache[page_id] = node
    self.node_cache.move_to_end(page_id)
    self._evict_node_if_needed()

def _evict_node_if_needed(self):
    if len(self.node_cache) > self.pool_size:
        self.node_cache.popitem(last=False)
```

This is very similar to our record caching but for the indexes (BTree), so the search is faster with both getting the record and indexing it.
