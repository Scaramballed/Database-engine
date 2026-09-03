Day 1 ~2 (I didn't really record day 1 cause it was mostly just me researching) 
— Slotted Pages

Today I learned how databases organize records inside fixed-size pages.

I started with a 4096-byte page and learned how the page can be divided into different regions:

- Page header
- Slot array
- Free space
- Record data

I learned how `struct` can be used to convert integers into bytes and store metadata directly inside the page.

### What I implemented

I implemented a `Page` class that can:

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
