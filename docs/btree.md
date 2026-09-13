# Btree indexing implementation

This file contains 2 classes, first is make the tree object itself (Btree) and the indexing part (BTreeIndex). I will be trying to cover it as thorougly as I can

## Formatings

```python
INDEX_META_PAGE_ID = 0

KEY_TYPE_INT = "int"
KEY_TYPE_STRING = "string"

STRING_KEY_SIZE = 20   # fixed max bytes per string key, same pattern as Schema's string columns

NODE_HEADER_FORMAT = ">BH"
NODE_HEADER_SIZE = struct.calcsize(NODE_HEADER_FORMAT)

CHILD_FORMAT = ">I"
CHILD_SIZE = struct.calcsize(CHILD_FORMAT)

def _key_format(key_type):
    return ">i" if key_type == KEY_TYPE_INT else f">{STRING_KEY_SIZE}s"

def _key_size(key_type):
    return struct.calcsize(_key_format(key_type))

def _leaf_entry_format(key_type):
    return _key_format(key_type) + "IH"

def _leaf_entry_size(key_type):
    return struct.calcsize(_leaf_entry_format(key_type))

def _max_keys_for(key_type):
    return (PAGE_SIZE - NODE_HEADER_SIZE) // _leaf_entry_size(key_type)
```

These are the fixed constants the whole B-tree index relies on. INDEX_META_PAGE_ID reserves page 0 for index metadata, same idea as META_PAGE_ID in Table. KEY_TYPE_INT/KEY_TYPE_STRING are just named string labels so the rest of the code compares against "int"/"string" consistently instead of typo-prone raw strings scattered everywhere. STRING_KEY_SIZE fixes how many bytes a string key is always allowed to take up — same fixed-width trick as Schema's string columns, needed here because a B-tree node's layout has to be predictable, so every string key must occupy the same number of bytes regardless of the actual word length. NODE_HEADER_FORMAT/NODE_HEADER_SIZE and CHILD_FORMAT/CHILD_SIZE precompute the format and byte-size for a node's header and for a single child pointer, so the rest of the file doesn't recompute struct.calcsize repeatedly.
`_key_format()` picks the right struct format depending on which kind of key this tree is using — a 4-byte int (">i") or a fixed-size byte string `(f">{STRING_KEY_SIZE}s"). _key_size()` just asks struct how many bytes that format actually takes up, so the rest of the code never has to hardcode a key's byte size — it's derived once, in one place.
A leaf entry is one key plus where it points to on disk, so `_leaf_entry_format()` builds on `_key_format()` by appending "IH" — an unsigned int for the page_id and an unsigned short for the slot_id, matching the (page_id, slot_id) location pairs you've been using everywhere else. `_leaf_entry_size()` again just converts that format into a byte count via struct.calcsize.
And finally we calculate how many key-entries can actually fit in one page: take the usable space (PAGE_SIZE minus whatever the header eats up), then divide by the size of a single entry. Integer division (//) rounds down, which is exactly right here — you can't fit a partial entry, so any leftover space just goes unused. This number is what the B-tree's split logic will check against when deciding a node is full.

## BTreeNode

```python
class BTreeNode:
    def __init__(self, key_type=KEY_TYPE_INT, is_leaf=True):
        self.key_type = key_type
        self.is_leaf = is_leaf
        self.keys = []
        self.children = []
        self.pointers = []
```

Here we are frankling speaking, just building the tree. We also set up a boolean for the `is_leaf` cause do not forget, the main information we need is going to be in the leafs, so it is True then we get that particular Node.

```python
def _encode_key(self, key):
    if self.key_type == KEY_TYPE_STRING:
        encoded = key.encode("utf-8")
        if len(encoded) > STRING_KEY_SIZE:
            raise ValueError(f"key '{key}' exceeds max index key size ({STRING_KEY_SIZE} bytes)")
        return encoded.ljust(STRING_KEY_SIZE, b"\x00")
    return key
def _decode_key(self, raw_key):
    if self.key_type == KEY_TYPE_STRING:
        return raw_key.rstrip(b"\x00").decode("utf-8")
    return raw_key
```

Here we are doing things as similar as it can get to the schema encode part, its just this time we encoding and decoding the keys.

```python
def to_bytes(self):
    buffer = bytearray(PAGE_SIZE)
    struct.pack_into(NODE_HEADER_FORMAT, buffer, 0, int(self.is_leaf), len(self.keys))

    leaf_entry_format = _leaf_entry_format(self.key_type)
    leaf_entry_size = _leaf_entry_size(self.key_type)
    key_format = _key_format(self.key_type)
    key_size = _key_size(self.key_type)

    offset = NODE_HEADER_SIZE
    if self.is_leaf:
        for key, (page_id, slot_id) in zip(self.keys, self.pointers):
            struct.pack_into(leaf_entry_format, buffer, offset, self._encode_key(key), page_id, slot_id)
            offset += leaf_entry_size
    else:
        # children interleave: child[0], key[0], child[1], key[1], ..., child[n]
        struct.pack_into(CHILD_FORMAT, buffer, offset, self.children[0])
        offset += CHILD_SIZE
        for key, child in zip(self.keys, self.children[1:]):
            struct.pack_into(key_format, buffer, offset, self._encode_key(key))
            offset += key_size
            struct.pack_into(CHILD_FORMAT, buffer, offset, child)
            offset += CHILD_SIZE

    return bytes(buffer)
```

`to_bytes()` serializes a BTreeNode into a fixed PAGE_SIZE chunk of bytes so it can be written to disk via `write_node()`. We use a bytearray instead of building the bytes up incrementally like `Schema.encode()` does, because struct.pack_into writes at a specific offset into an existing buffer rather than producing new bytes each call, necessary here since we're placing variable numbers of entries at increasing offsets rather than packing everything in one call.

The header is written first: `int(self.is_leaf)` (as 0/1, since struct can't pack a bool directly) and len(self.keys), so from_bytes() later knows both what kind of node this is and how many entries to read back out — same role count plays in Table.`_write_metadata()`.

The format/size helpers are computed once up front rather than inside the loop, since they don't change per iteration and there's no reason to recompute them repeatedly.

Leaf nodes store (key, page_id, slot_id) triples, because a leaf is the thing that actually points to where a row physically lives, that's the whole reason the tree exists, to get you from a key to a location. offset walks forward by leaf_entry_size after each entry so every triple lands at its own non-overlapping position in the buffer.

Internal nodes are where the real logic lives. A node with N keys always has exactly N+1 children — a key doesn't belong "inside" one child, it marks the boundary between two children: everything smaller than key[0] lives down children[0], everything between key[0] and key[1] lives down children[1], and so on, with the last child holding everything larger than the final key. That's why children[0] is written alone before the loop even starts — it's the one child with no key before it — and the loop then zips self.keys against self.children[1:], writing key[i] immediately followed by children[i+1], producing the interleaved layout child, key, child, key, ..., child the comment describes. Slicing self.children[1:] is required, not cosmetic, without it, zip would stop one pair early and silently drop the last child, since zip always stops at the shorter sequence.

```python
@classmethod
def from_bytes(cls, data, key_type=KEY_TYPE_INT):
    is_leaf_int, num_keys = struct.unpack_from(NODE_HEADER_FORMAT, data, 0)
    node = cls(key_type=key_type, is_leaf=bool(is_leaf_int))

    leaf_entry_format = _leaf_entry_format(key_type)
    leaf_entry_size = _leaf_entry_size(key_type)
    key_format = _key_format(key_type)
    key_size = _key_size(key_type)

    offset = NODE_HEADER_SIZE
    if node.is_leaf:
        for _ in range(num_keys):
            raw_key, page_id, slot_id = struct.unpack_from(leaf_entry_format, data, offset)
            node.keys.append(node._decode_key(raw_key))
            node.pointers.append((page_id, slot_id))
            offset += leaf_entry_size
    else:
        first_child = struct.unpack_from(CHILD_FORMAT, data, offset)[0]
        node.children.append(first_child)
        offset += CHILD_SIZE
        for _ in range(num_keys):
            raw_key = struct.unpack_from(key_format, data, offset)[0]
            offset += key_size
            child = struct.unpack_from(CHILD_FORMAT, data, offset)[0]
            offset += CHILD_SIZE
            node.keys.append(node._decode_key(raw_key))
            node.children.append(child)

    return node
```

Same as to_bytes nothing new worth mentioning done here. But this time we take the bytes into raw data, hence return the node.

## BTreeIndex

```python
class BTreeIndex:
def __init__(self, page_manager, key_type=KEY_TYPE_INT):
    self.page_manager = page_manager
    self.key_type = key_type
    self.max_keys = _max_keys_for(key_type)

    if self.page_manager.is_new():
        self.root_page_id = 0
        self._write_index_metadata()
        root = BTreeNode(key_type=self.key_type, is_leaf=True)
        self.root_page_id = self._allocate_node(root)
        self._write_index_metadata()
    else:
        self._load_index_metadata()
```

This is the entry point for building or reopening a B-tree `index. self.max_keys = _max_keys_for(key_type)` stores the ceiling on how many keys a leaf node can hold, computed once here instead of recalculated later whenever a split decision needs to be made.

If `page_manager.is_new()`, we're bootstrapping a brand-new, empty index, so a root node gets created. That root starts as a leaf — not because it happens to be the only page that exists, but because an empty tree has nothing to route to yet: internal nodes only exist to point toward leaves holding real data, so with zero entries there's no need for any routing structure at all. Internal nodes only get created later, the first time this root fills past max_keys and splits.

One quirk worth noting here: `self.root_page_id = 0` is set as a placeholder before the real root page is allocated.

If the page manager isn't new, there's already a real index on disk, so instead of bootstrapping anything, `_load_index_metadata()` reads back the previously-persisted `root_page_id` and picks up exactly where the index left off — same pattern as `Table._load_metadata()`.

```python
def _write_index_metadata(self):
    data = struct.pack("<I", self.root_page_id)
    padded = data.ljust(PAGE_SIZE, b"\x00")
    self.page_manager.write_raw(INDEX_META_PAGE_ID, padded)

def _load_index_metadata(self):
    raw = self.page_manager.read_raw(INDEX_META_PAGE_ID)
    self.root_page_id = struct.unpack_from("<I", raw, 0)[0]
```

Same pattern as Table`._write_metadata()`/`_load_metadata()`, just simpler — the index only needs to persist one value, root_page_id, rather than a variable-length list of page IDs, so there's no count prefix needed here.

`_write_index_metadata()` packs root_page_id as a single unsigned int, pads it out to a full PAGE_SIZE (same reasoning as before — every page slot on disk is fixed-size, so the write has to match that regardless of how few real bytes are actually meaningful), and writes it to the reserved `INDEX_META_PAGE_ID` slot via `write_raw()`.

`_load_index_metadata()` reads that same page back and unpacks just the first 4 bytes as the root's page ID, ignoring the rest of the padding — mirroring `_load_metadata()'s` `struct.unpack_from("<I", raw, 0)[0]` call for reading count.

```python
def _read_node(self, page_id):
    return self.page_manager.read_node(page_id, self.key_type)

def _write_node(self, page_id, node):
    self.page_manager.write_node(page_id, node)

def _allocate_node(self, node):
    page_id = self.page_manager.allocate_page()
    self._write_node(page_id, node)
    return page_id
```

These are just helper functions re using the page_manager's functions. Does the same things but with nodes, read, write and allocate node.

### From this point forward

The actual logic begins here (as some might say, the hard part), so I will sometimes explain it in points as well.

```python
def search(self, key):
    page_id = self.root_page_id
    node = self._read_node(page_id)

    while not node.is_leaf:
        i = 0
        while i < len(node.keys) and key >= node.keys[i]:
            i += 1
        page_id = node.children[i]
        node = self._read_node(page_id)

    for i, k in enumerate(node.keys):
        if k == key:
            return node.pointers[i]
    return None
```

- Walk left-to-right through this node's sorted keys to find where `key` fits (`i` ends up as that position).
- If `node.keys[i] == key` exactly, found it here.
- If this is a leaf and no match, the key doesn't exist anywhere.
- Otherwise recurse into `children[i]` — the same `i` doubles as both "match position" and "which child leads to the right range."

### Insert Overview

Here there are 2 entry points that work together.

- `insert(key)`,public method. Only special-cases the root
- `_insert_non_full(node, key)` — does the real work, walking downward.

**Design choice: split BEFORE inserting, not after.** Every full node is split the moment _before_ you'd step into it — never after overflowing it. This guarantees `_insert_non_full` is always called on a node that's guaranteed to have room, so there's no need to ever backtrack up the tree after the fact.

```python
def insert(self, key):
    root = self.root

    if len(root.keys) >= self.max_keys:
        new_root = BTreeNode(is_leaf=False)
        new_root.children.append(root)
        self._split_child(new_root, 0)
        self.root = new_root

    self._insert_non_full(self.root, key)
```

- The root is special because it has no parent to promote a key into. If it's full, manufacture a brand new empty parent above it first, make the old root its only child, then split that child.
- This is the only place the tree's height increases.

```python
def _insert_non_full(self, node, key):
    i = len(node.keys) - 1

    if node.is_leaf:
        # actual insertion happens here — nowhere else
        node.keys.append(None)
        while i >= 0 and key < node.keys[i]:
            node.keys[i + 1] = node.keys[i]
            i -= 1
        node.keys[i + 1] = key
    else:
        # not there yet — find the right child, split it if full, then recurse
        while i >= 0 and key < node.keys[i]:
            i -= 1
        i += 1

        if len(node.children[i].keys) >= self.max_keys:
            self._split_child(node, i)
            if key > node.keys[i]:
                i += 1

        self._insert_non_full(node.children[i], key)
```

The leaf-case shifting loop is a manual **insertion sort**: shift everything bigger than `key` one slot right, then drop `key` into the gap.

The `if key > node.keys[i]: i += 1` correction exists because splitting a child _changes what sits at `children[i]`_ — after a split, the key you're inserting might now belong in the _new_ right-hand sibling instead of the original left-hand one, so `i` needs to be re-checked against the (now different) parent key at that position.

### Spliting mechanics

```python
def _split_child(self, parent, index):
    full_child = parent.children[index]
    mid = len(full_child.keys) // 2
    median_key = full_child.keys[mid]

    left = BTreeNode(is_leaf=full_child.is_leaf)
    right = BTreeNode(is_leaf=full_child.is_leaf)

    left.keys = full_child.keys[:mid]
    right.keys = full_child.keys[mid + 1:]

    if not full_child.is_leaf:
        left.children = full_child.children[:mid + 1]
        right.children = full_child.children[mid + 1:]

    parent.children[index] = left
    parent.children.insert(index + 1, right)
    parent.keys.insert(index, median_key)
```

Using `full_child.keys = [5, 10, 15]`:

- `mid = 3 // 2 = 1` → always the same index for a given `max_keys` (every full node has exactly `max_keys` keys when it splits, so `mid` never varies — only the _value_ sitting at that index does).
- `median_key = keys[1] = 10`
- `left.keys = keys[:1] = [5]`
- `right.keys = keys[2:] = [15]`
- `10` is not discarded — it gets promoted into the parent, not copied into either half.

**Why not `statistics.median()`?** Two reasons: (1) for even-length lists it _averages_ the two middle values, producing a number that was never an actual key in your data — but the median here must be a real existing key, since it physically moves into the parent. (2) You need the _index_ to slice the list around, not just the value — `len(keys)//2` gives you both a position and (via indexing) the value, in one step.

**Redistributing children (only when `full_child` is NOT a leaf):**

Say `full_child.keys = [10, 20, 30]` with `children = [C0, C1, C2, C3]`:

```text
 C0    10    C1    20    C2    30    C3
```

After split (`mid = 1`, median = `20`, `left.keys=[10]`, `right.keys=[30]`):

- `left` needs `len(keys)+1 = 2` children → the ones on the left side of the cut: `C0, C1`
- `right` needs `2` children → the ones on the right side: `C2, C3`

```python
left.children  = full_child.children[:mid + 1]   # [:2] -> [C0, C1]
right.children = full_child.children[mid + 1:]   # [2:] -> [C2, C3]
```

The `+1` on the children slice (vs. plain `mid` for keys) exists because children always outnumber keys by one — the slice boundary has to sit one position further right than the key boundary.

Check the invariant after: `left` → 1 key, 2 children (2 == 1+1 ✓). `right` → 1 key, 2 children (2 == 1+1 ✓). Both are valid standalone nodes.

**Grafting back into the parent:**

```python
parent.children[index] = left            # old full node replaced by left half
parent.children.insert(index + 1, right) # right half inserted right after
parent.keys.insert(index, median_key)    # median inserted at matching position
```

One slot becomes two; the promoted key sits exactly between them.

### Full worked trace

Starting empty, `max_keys = 3`, inserting: `10, 20, 30, 15, 25, 5, 35, 1`

**Insert 10, 20, 30** — root fills normally, no split yet:

```text
root: [10, 20, 30]
```

**Insert 15** — `insert()`'s root check fires: `len([10,20,30]) >= 3` → True. Split the old root before doing anything else. Median of `[10,20,30]` is `20`. New root born:

```text
        [20]
       /    \
    [10]   [30]
```

Now `_insert_non_full(root, 15)` runs: `15 < 20` → go left → `[10]` not full → insert → `[10, 15]`.

```text
        [20]
       /    \
   [10,15]  [30]
```

**Insert 25** — root not full. `25 > 20` → right child `[30]`, not full → `[25, 30]`.

```text
        [20]
       /    \
   [10,15]  [25,30]
```

**Insert 5** — `5 < 20` → left child `[10,15]`, not full → `[5,10,15]`.

```text
        [20]
       /    \
[5,10,15]  [25,30]
```

**Insert 35** — `35 > 20` → right child `[25,30]`, not full → `[25,30,35]`.

```text
        [20]
       /    \
[5,10,15]  [25,30,35]
```

**Insert 1** — root `[20]` not full (no root-level split this time). `_insert_non_full(root, 1)`: `1 < 20` → about to enter `children[0] = [5,10,15]` — **full!** (`len == 3`). Mid-tree split fires (this time from inside `_insert_non_full`'s `else` branch, not `insert()`'s root check):

- Split `[5,10,15]`: median `10` promoted, left `[5]`, right `[15]`.
- Root becomes `[10, 20]`, children become `[[5], [15], [25,30,35]]`.
- Correction check: `1 > node.keys[0]`? `1 > 10`? No → `i` stays `0`.
- Recurse into `children[0] = [5]` → insert `1` → `[1, 5]`.

**Final tree:**

```text
              [10, 20]
             /   |    \
        [1,5]  [15]  [25,30,35]
```

This single trace hits every mechanism: normal leaf insertion, a **root split** (via `insert()`'s check), and a **mid-tree split with index correction** (via `_insert_non_full`'s check).
