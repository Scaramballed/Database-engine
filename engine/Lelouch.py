import os
from engine.Pages import PageManager
from engine.record import Schema
from engine.Table import Table

for f in ("lelouch.db", "lelouch_id_index.db"):
    if os.path.exists(f):
        os.remove(f)

pm = PageManager("lelouch.db")
index_pm = PageManager("lelouch_id_index.db")
schema = Schema([("id", "int"), ("name", "str", 20)])
table = Table(pm, schema, index_page_manager=index_pm, index_column="id")

import random
import string

for i in range(1, 5001):
    name = "".join(random.choices(string.ascii_letters, k=8))
    table.insert_record((i, name))
    if i % 500 == 0:
        print(f"Inserted {i} records...")

pm.close()
index_pm.close()
print("Done.")