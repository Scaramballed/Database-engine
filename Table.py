from Pages import Page, PageManager, PAGE_SIZE, SLOT_SIZE
from record import Schema

class Table:
    def __init__(self, page_manager, schema):
        self.page_manager = page_manager
        self.schema = schema
        self.page_ids = [] 
        #just a list of page_ids that have been allocated for this table. We will use this to find pages when we want to insert or retrieve records.         
    def insert_record(self, values):
        record_bytes = self.schema.encode(values)

        if self.page_ids:
            last_page_id = self.page_ids[-1] #-1 cause the last past id
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
        raw = page.get_record(slot_id)
        return self.schema.decode(raw)

    def delete_record(self, page_id, slot_id):
        page = self.page_manager.read_page(page_id)
        page.delete_record(slot_id)
        self.page_manager.write_page(page_id, page)

    def update_record(self, page_id, slot_id, values):
        new_bytes = self.schema.encode(values)
        page = self.page_manager.read_page(page_id)
        page.update_record(slot_id, new_bytes)
        self.page_manager.write_page(page_id, page)







#only for testing purposes, lmao so dont mind it much
if __name__ == "__main__":
    import os

    DB_FILE = "test.db"
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE) 

    pm = PageManager(DB_FILE)
    schema = Schema([("id", "int"), ("name", "str", 20)])
    table = Table(pm, schema)

    print(f"PAGE_SIZE = {PAGE_SIZE}\n")

    people = [(1, "Scara"), (2, "Siddhartha"), (3, "Bhusal")]

    locations = []
    for i, person in enumerate(people):
        loc = table.insert_record(person)
        locations.append(loc)
        print(f"Inserted record {i:2d} {person} -> {loc}   | page_ids so far: {table.page_ids}")

    print(f"\nFinal page_ids: {table.page_ids}")
    print(f"Total pages allocated: {len(table.page_ids)}")
    print("\n--- Reading back all records ---")
    for i, (page_id, slot_id) in enumerate(locations):
        decoded = table.get_record(page_id, slot_id)
        matches = ((decoded["id"], decoded["name"]) == people[i])
        print(f"record {i}: decoded={decoded}  matches original: {matches}")

    #verifyin the delete shi as well
    print("\n--- Deleting record 0 and confirming it's gone ---")
    page_id, slot_id = locations[0]
    table.delete_record(page_id, slot_id)
    try:
        table.get_record(page_id, slot_id)
        print("ERROR: record 0 should have raised, but didn't")
    except Exception as e:
        print(f"Confirmed deleted: {e}")

    print("\n--- Updating record 1 ---")
    page_id, slot_id = locations[1]
    table.update_record(page_id, slot_id, (2, "Sid"))
    print(f"after update: {table.get_record(page_id, slot_id)}")

    print("\n--- Closing and reopening the file to check persistence ---")
    pm.close()

    pm2 = PageManager(DB_FILE)
    page_id, slot_id = locations[2]
    data = pm2.read_page(page_id).get_record(slot_id)
    decoded = schema.decode(data)
    print(f"record 2 read after reopening file: decoded={decoded}  matches original = {(decoded['id'], decoded['name']) == people[2]}")
    pm2.close()