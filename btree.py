import struct
from Pages import PAGE_SIZE   
MAX_KEYS = 400
INDEX_META_PAGE_ID = 0   

NODE_HEADER_FORMAT = ">BH"     
NODE_HEADER_SIZE = struct.calcsize(NODE_HEADER_FORMAT)

LEAF_ENTRY_FORMAT = ">iIH"     
LEAF_ENTRY_SIZE = struct.calcsize(LEAF_ENTRY_FORMAT)

KEY_FORMAT = ">i"
KEY_SIZE = struct.calcsize(KEY_FORMAT)

CHILD_FORMAT = ">I"
CHILD_SIZE = struct.calcsize(CHILD_FORMAT)

class BTreeNode:
    def __init__(self, is_leaf=True):
        self.is_leaf = is_leaf
        self.keys = []          
        self.children = []       
        self.pointers = []      
    def to_bytes(self):
        buffer = bytearray(PAGE_SIZE)
        struct.pack_into(NODE_HEADER_FORMAT, buffer, 0, int(self.is_leaf), len(self.keys))

        offset = NODE_HEADER_SIZE
        if self.is_leaf:
            for key, (page_id, slot_id) in zip(self.keys, self.pointers):
                struct.pack_into(LEAF_ENTRY_FORMAT, buffer, offset, key, page_id, slot_id)
                offset += LEAF_ENTRY_SIZE
        else:
            # children interleave: child[0], key[0], child[1], key[1], ..., child[n]
            struct.pack_into(CHILD_FORMAT, buffer, offset, self.children[0])
            offset += CHILD_SIZE
            for key, child in zip(self.keys, self.children[1:]):
                struct.pack_into(KEY_FORMAT, buffer, offset, key)
                offset += KEY_SIZE
                struct.pack_into(CHILD_FORMAT, buffer, offset, child)
                offset += CHILD_SIZE

        return bytes(buffer)

    @classmethod
    def from_bytes(cls, data):
        is_leaf_int, num_keys = struct.unpack_from(NODE_HEADER_FORMAT, data, 0)
        node = cls(is_leaf=bool(is_leaf_int))

        offset = NODE_HEADER_SIZE
        if node.is_leaf:
            for _ in range(num_keys):
                key, page_id, slot_id = struct.unpack_from(LEAF_ENTRY_FORMAT, data, offset)
                node.keys.append(key)
                node.pointers.append((page_id, slot_id))
                offset += LEAF_ENTRY_SIZE
        else:
            first_child = struct.unpack_from(CHILD_FORMAT, data, offset)[0]
            node.children.append(first_child)
            offset += CHILD_SIZE
            for _ in range(num_keys):
                key = struct.unpack_from(KEY_FORMAT, data, offset)[0]
                offset += KEY_SIZE
                child = struct.unpack_from(CHILD_FORMAT, data, offset)[0]
                offset += CHILD_SIZE
                node.keys.append(key)
                node.children.append(child)

        return node


class BTreeIndex:
    def __init__(self, page_manager):
        self.page_manager = page_manager

        if self.page_manager.is_new():
            self.root_page_id = 0
            self._write_index_metadata()
            root = BTreeNode(is_leaf=True)
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

    def _read_node(self, page_id):
        raw = self.page_manager.read_raw(page_id)
        return BTreeNode.from_bytes(raw)

    def _write_node(self, page_id, node):
        self.page_manager.write_raw(page_id, node.to_bytes())

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

        if len(root.keys) >= MAX_KEYS:
            new_root = BTreeNode(is_leaf=False)
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

            if len(child.keys) >= MAX_KEYS:
                self._split_child(page_id, node, i)
                node = self._read_node(page_id)
                if key >= node.keys[i]:
                    i += 1

            self._insert_non_full(node.children[i], key, ptr_page_id, slot_id)

    def _split_child(self, parent_page_id, parent, index):
        full_child_id = parent.children[index]
        full_child = self._read_node(full_child_id)

        mid = len(full_child.keys) // 2

        left = BTreeNode(is_leaf=full_child.is_leaf)
        right = BTreeNode(is_leaf=full_child.is_leaf)

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