import struct
from engine.constants import PAGE_SIZE
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


class BTreeNode:
    def __init__(self, key_type=KEY_TYPE_INT, is_leaf=True):
        self.key_type = key_type
        self.is_leaf = is_leaf
        self.keys = []
        self.children = []
        self.pointers = []

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

    def _write_index_metadata(self):
        data = struct.pack("<I", self.root_page_id)
        padded = data.ljust(PAGE_SIZE, b"\x00")
        self.page_manager.write_raw(INDEX_META_PAGE_ID, padded)

    def _load_index_metadata(self):
        raw = self.page_manager.read_raw(INDEX_META_PAGE_ID)
        self.root_page_id = struct.unpack_from("<I", raw, 0)[0]

    """calling the cache methods from the page manager to read and write nodes, so that we can manage the cache for BTreeNodes separately from Pages."""
    def _read_node(self, page_id):
        return self.page_manager.read_node(page_id, self.key_type)

    def _write_node(self, page_id, node):
        self.page_manager.write_node(page_id, node)

    def _allocate_node(self, node):
        page_id = self.page_manager.allocate_page()
        self._write_node(page_id, node)
        return page_id

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

    def insert(self, key, ptr_page_id, slot_id):
        root = self._read_node(self.root_page_id)

        if len(root.keys) >= self.max_keys:
            new_root = BTreeNode(key_type=self.key_type, is_leaf=False)
            new_root.children.append(self.root_page_id)
            new_root_id = self._allocate_node(new_root)
            self._split_child(new_root_id, new_root, 0)
            self.root_page_id = new_root_id
            self._write_index_metadata()

        self._insert_non_full(self.root_page_id, key, ptr_page_id, slot_id)

    def _insert_non_full(self, page_id, key, ptr_page_id, slot_id):
        node = self._read_node(page_id)
        i = len(node.keys) - 1

        if node.is_leaf:
            node.keys.append(None)
            node.pointers.append(None)
            while i >= 0 and key < node.keys[i]:
                node.keys[i + 1] = node.keys[i]
                node.pointers[i + 1] = node.pointers[i]
                i -= 1
            node.keys[i + 1] = key
            node.pointers[i + 1] = (ptr_page_id, slot_id)
            self._write_node(page_id, node)
        else:
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1

            child_id = node.children[i]
            child = self._read_node(child_id)

            if len(child.keys) >= self.max_keys:
                self._split_child(page_id, node, i)
                node = self._read_node(page_id)
                if key >= node.keys[i]:
                    i += 1

            self._insert_non_full(node.children[i], key, ptr_page_id, slot_id)

    def _split_child(self, parent_page_id, parent, index):
        full_child_id = parent.children[index]
        full_child = self._read_node(full_child_id)

        mid = len(full_child.keys) // 2

        left = BTreeNode(key_type=self.key_type, is_leaf=full_child.is_leaf)
        right = BTreeNode(key_type=self.key_type, is_leaf=full_child.is_leaf)

        if full_child.is_leaf:
            median_key = full_child.keys[mid]
            left.keys = full_child.keys[:mid]
            left.pointers = full_child.pointers[:mid]
            right.keys = full_child.keys[mid:]
            right.pointers = full_child.pointers[mid:]
        else:
            median_key = full_child.keys[mid]
            left.keys = full_child.keys[:mid]
            left.children = full_child.children[:mid + 1]
            right.keys = full_child.keys[mid + 1:]
            right.children = full_child.children[mid + 1:]

        left_id = self._allocate_node(left)
        right_id = self._allocate_node(right)

        parent.children[index] = left_id
        parent.children.insert(index + 1, right_id)
        parent.keys.insert(index, median_key)
        self._write_node(parent_page_id, parent)