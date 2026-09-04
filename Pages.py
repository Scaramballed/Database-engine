import struct
PAGE_SIZE = 4096
HEADER_FORMAT = "<HH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
SLOT_FORMAT = "<HH"
SLOT_SIZE = struct.calcsize(SLOT_FORMAT)
class Page:
    def __init__(self):
        self.buffer = bytearray (PAGE_SIZE)
        self.num_slots = 0
        self.free_space_offset = PAGE_SIZE
        self._write_header()
    def _write_header(self):
        struct.pack_into(HEADER_FORMAT, self.buffer, 0, self.num_slots, self.free_space_offset)
    def _slot_offset(self, slot_index):
        return HEADER_SIZE + slot_index * SLOT_SIZE
    def free_space(self):
        slot_array_end = HEADER_SIZE + self.num_slots * SLOT_SIZE
        return self.free_space_offset - slot_array_end
    def insert_record(self, record):
        record_size = len(record)
        if self.free_space()<record_size + SLOT_SIZE:
            raise Exception("Not enough space to insert record")
        self.free_space_offset -=record_size
        self.buffer[self.free_space_offset:self.free_space_offset +record_size] = record
        slot_id = self.num_slots
        struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id), self.free_space_offset, record_size)
        self.num_slots +=1
        self._write_header()
        return slot_id
    def get_record(self, slot_id):
        offset, length = struct.unpack_from(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id)) #understand the signature of this
        if length == 0:
            raise Exception("Record has been deleted")
        return bytes(self.buffer[offset:offset + length])
    def delete_record(self, slot_id):
        offset, _ = struct.unpack_from(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id))
        self._slot_offset(slot_id) #understand this again
        struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id), offset, 0)
    def update_record(self, slot_id, new_bytes):
        old_offset, old_length = struct.unpack_from(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id))

        if len(new_bytes) <= old_length:
            # fits in the old space — overwrite in place, keep old_length in the slot
            self.buffer[old_offset:old_offset + len(new_bytes)] = new_bytes
            struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id), old_offset, len(new_bytes))
        else:
            # since it doesnt fit we just kinda point it to a new location in the free space, and update the slot to point to that new location. The old space is now wasted, but we can reclaim it later when we compact the page.
            if self.free_space() < len(new_bytes):
                raise ValueError("Page full")
            self.free_space_offset -= len(new_bytes)
            self.buffer[self.free_space_offset:self.free_space_offset + len(new_bytes)] = new_bytes
            struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id), self.free_space_offset, len(new_bytes))
            self._write_header()
    def to_bytes(self):
        return bytes(self.buffer)
    @classmethod
    def from_bytes(cls, data):
        page = cls.__new__(cls)
        page.buffer = bytearray(data)
        page.num_slots, page.free_space_offset = struct.unpack_from(HEADER_FORMAT, page.buffer, 0)
        return page
    

#Manages reading and writing pages to a file
class PageManager:
    def __init__(self, filename):
        try:
            self.file = open(filename, "r+b")
        except FileNotFoundError:
            open(filename, "wb").close() #written on one line without bothering to save it to a variable, since we never need to use it again after opening it.
            self.file = open(filename, "r+b")
    def allocate_page(self):
        self.file.seek(0, 2)
        file_size = self.file.tell()
        return file_size // PAGE_SIZE

    def write_page(self, page_id, page):
        offset = page_id * PAGE_SIZE
        self.file.seek(offset)
        self.file.write(page.to_bytes())   # page is a Page object passed in

    def read_page(self, page_id):
        offset = page_id * PAGE_SIZE
        self.file.seek(offset)
        data = self.file.read(PAGE_SIZE)
        return Page.from_bytes(data)

    def close(self):
        self.file.close()
