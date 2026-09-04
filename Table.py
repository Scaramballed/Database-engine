from Pages import Page, PageManager, PAGE_SIZE, SLOT_SIZE


class Table:
    def __init__(self, page_manager):
        self.page_manager = page_manager
        self.page_ids = []          
    def insert_record(self, record_bytes):
        if self.page_ids:
            last_page_id = self.page_ids[-1]
            page = self.page_manager.read_page(last_page_id)

            if page.free_space() >= len(record_bytes) + SLOT_SIZE:
                slot_id = page.insert_record(record_bytes)
                self.page_manager.write_page(last_page_id, page)
                return (last_page_id, slot_id)
        new_page_id = self.page_manager.allocate_page()
        new_page = Page()
        slot_id = new_page.insert_record(record_bytes)
        self.page_manager.write_page(new_page_id, new_page)
        self.page_ids.append(new_page_id)

        return (new_page_id, slot_id)

    def get_record(self, page_id, slot_id):
        page = self.page_manager.read_page(page_id)
        return page.get_record(slot_id)

    def delete_record(self, page_id, slot_id):
        page = self.page_manager.read_page(page_id)
        page.delete_record(slot_id)
        self.page_manager.write_page(page_id, page)


if __name__ == "__main__":
    import os

    DB_FILE = "test.db"
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE) 

    pm = PageManager(DB_FILE)
    table = Table(pm)

    print(f"PAGE_SIZE = {PAGE_SIZE}\n")


    records = [f"record number {i}: {'x' * 400}".encode() for i in range(12)]

    locations = []
    for i, record in enumerate(records):
        loc = table.insert_record(record)
        locations.append(loc)
        print(f"Inserted record {i:2d} (size={len(record):4d} bytes) -> {loc}   | page_ids so far: {table.page_ids}")

    print(f"\nFinal page_ids: {table.page_ids}")
    print(f"Total pages allocated: {len(table.page_ids)}")
    print("\n--- Reading back a few records ---")
    for i in [0, 5, 11]:
        page_id, slot_id = locations[i]
        data = table.get_record(page_id, slot_id)
        matches = (data == records[i])
        print(f"record {i}: location={locations[i]}  matches original: {matches}")

    # --- verify delete works ---
    print("\n--- Deleting record 3 and confirming it's gone ---")
    page_id, slot_id = locations[3]
    table.delete_record(page_id, slot_id)
    try:
        table.get_record(page_id, slot_id)
        print("ERROR: record 3 should have raised, but didn't")
    except Exception as e:
        print(f"Confirmed deleted: {e}")

    print("\n--- Closing and reopening the file to check persistence ---")
    pm.close()

    pm2 = PageManager(DB_FILE)
    page_id, slot_id = locations[7]
    data = pm2.read_page(page_id).get_record(slot_id)
    print(f"record 7 read after reopening file: matches original = {data == records[7]}")
    pm2.close()