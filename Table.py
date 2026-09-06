import struct
from Pages import Page, PageManager, PAGE_SIZE, SLOT_SIZE
from record import Schema
from btree import BTreeIndex  

META_PAGE_ID = 0

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
            self.index = BTreeIndex(index_page_manager)

    def _write_metadata(self):
        count = len(self.page_ids)
        data = struct.pack(f"<I{count}I", count, *self.page_ids)
        padded = data.ljust(PAGE_SIZE, b"\x00")
        self.page_manager.write_raw(META_PAGE_ID, padded)

    def _load_metadata(self):
        raw = self.page_manager.read_raw(META_PAGE_ID)
        count = struct.unpack_from("<I", raw, 0)[0]
        self.page_ids = list(struct.unpack_from(f"<{count}I", raw, 4)) if count else []

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

    def get_record(self, page_id, slot_id):
        page = self.page_manager.read_page(page_id)
        raw = page.get_record(slot_id)
        return self.schema.decode(raw)

    # ADDED
    def _update_index(self, values, page_id, slot_id):
        if self.index is None:
            return
        column_names = [col[0] for col in self.schema.columns]
        key = values[column_names.index(self.index_column)]
        self.index.insert(key, page_id, slot_id)

    # ADDED
    def get_record_by_index(self, key):
        if self.index is None:
            raise ValueError("This table has no index configured")
        location = self.index.search(key)
        if location is None:
            return None
        page_id, slot_id = location
        return self.get_record(page_id, slot_id)

if __name__ == "__main__":
    import os

    DB_FILE = "test.db"
    INDEX_FILE = "test_id_index.db"
    for f in (DB_FILE, INDEX_FILE):
        if os.path.exists(f):
            os.remove(f)

    pm = PageManager(DB_FILE)
    index_pm = PageManager(INDEX_FILE)
    schema = Schema([("id", "int"), ("name", "str", 20)])
    table = Table(pm, schema, index_page_manager=index_pm, index_column="id")

    people = [(1, "Scara"), (2, "Siddhartha"), (3, "Bhusal"), (4, "Test"), (5, "Another")]

    for person in people:
        loc = table.insert_record(person)
        print(f"Inserted {person} -> {loc}")

    print("\n--- Searching via index ---")
    for target_id in [1, 3, 5, 999]:
        result = table.get_record_by_index(target_id)
        print(f"search id={target_id} -> {result}")

    print("\n--- Closing and reopening both files ---")
    pm.close()
    index_pm.close()

    pm2 = PageManager(DB_FILE)
    index_pm2 = PageManager(INDEX_FILE)
    table2 = Table(pm2, schema, index_page_manager=index_pm2, index_column="id")

    print(f"Reloaded page_ids: {table2.page_ids}")
    print(f"Reloaded index root_page_id: {table2.index.root_page_id}")

    for target_id in [2, 4]:
        result = table2.get_record_by_index(target_id)
        print(f"after reload, search id={target_id} -> {result}")