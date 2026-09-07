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
            index_col_type = next(col[1] for col in schema.columns if col[0] == index_column)  
            key_type = "string" if index_col_type == "str" else "int"                            
            self.index = BTreeIndex(index_page_manager, key_type=key_type)                      

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
