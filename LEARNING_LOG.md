Day 1 ~2 (I didn't really record day 1 cause it was mostly just me researching) 
— Slotted Pages

Today I learned how databases organize records inside fixed-size pages.

I started with a 4096-byte page and learned how the page can be divided into different regions:

- Page header
- Slot array
- Free space
- Record data

Implemented a `Page` class that can:

- Create a 4096-byte page using `bytearray`
- Store the number of slots in the page header
- Store the free-space offset in the page header
- Calculate the location of a slot using its `slot_id`
- Insert variable-length records
- Store each record's offset and length in a slot
- Retrieve records using their slot ID
- Delete records by marking their slot as empty
- Convert the page into raw bytes with `to_bytes()`
- Reconstruct a `Page` object from raw bytes with `from_bytes()`


Day 3
Understood some struct sinatures deeply enough to do everything from scratch again, and built a schema aware encode and decode layer on top of Page and Table.

Also reviewed my codes and found some bugs so fixed them as well. Implemented a tester for my Table. It was actually my first time implementing a tester so it was pretty interesting.
Honestly a lot of progress from day 1~2, I spent like 6 hours on this so yea. 
Either ways, tomorrow am planning to complete my storage engine.


