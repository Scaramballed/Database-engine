Day 1~2
(I didn't really record day 1 cause it was mostly just me researching)
— Slotted Pages

Today I learned how databases organize records inside fixed-size pages.

I started with a 4096-byte page and learned how the page can be divided into different regions:

Page header
Slot array
Free space
Record data

Implemented a Page class that can:
Create a 4096-byte page using bytearray
Store the number of slots in the page header
Store the free-space offset in the page header
Calculate the location of a slot using its slot_id
Insert variable-length records
Store each record's offset and length in a slot
Retrieve records using their slot ID
Delete records by marking their slot as empty
Convert the page into raw bytes with to_bytes()
Reconstruct a Page object from raw bytes with from_bytes()

Day 3
Understood some struct sinatures deeply enough to do everything from scratch again, and built a schema aware encode and decode layer on top of Page and Table.

Also reviewed my codes and found some bugs so fixed them as well. Implemented a tester for my Table. It was actually my first time implementing a tester so it was pretty interesting.
Honestly a lot of progress from day 1~2, I spent like 6 hours on this so yea.
Either ways, tomorrow am planning to complete my storage engine.

Day 4
Understood some struct sinatures deeply enough to do everything from scratch again, and built a schema aware encode and decode layer on top of Page and Table.

Also reviewed my codes and found some bugs so fixed them as well. Implemented a tester for my Table. It was actually my first time implementing a tester so it was pretty interesting.

In the day 4 thought, could implement everything that I have done till now from scratch, and then I moved to basic caching without LRU, then after understanding and implementing that did the LRU part as well.

And finally at the end I will try understanding B trees for the indexing. This will probably take a long time so for few days I will probably be only focused on the conceptes.
I did say I would finish the storage engine yesterday lmao, but yea I did underestimate the B-tree a lot ig.

Day 5
A lot happened today, I spend almost more than 8 hours on trying to implement the B tree algorithm that I learned yesterday into my engine. The toughest part was the wiring later on, especially one line in that update index took me a lot of time to come up with. Over all a very productive day, I even wrote notes with explaination behind every line of code I wrote. I left the debugging to the LLM though. There was a recursion issue in the metadata method which I just couldn't solve it. Either ways a very productive day with being able to sucessfully integrate the B tree indexing into my storage engine and testing was sucessful as well. Honestly very proud how far I am into this already.