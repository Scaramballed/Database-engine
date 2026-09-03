import struct

PAGE_SIZE = 4096

HEADER_FORMAT = ">HH"           # num_slots, free_space_offset — both unsigned short
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)   # 4 bytes

SLOT_FORMAT = ">HH"             # offset, length — both unsigned short
SLOT_SIZE = struct.calcsize(SLOT_FORMAT)       # 4 bytes


class Page:
    def __init__(self):
        self.buffer = bytearray(PAGE_SIZE)
        self.num_slots = 0
        self.free_space_offset = PAGE_SIZE   # record data grows downward from here
        self._write_header()

    def _write_header(self):
        struct.pack_into(HEADER_FORMAT, self.buffer, 0,
                          self.num_slots, self.free_space_offset)

    def _slot_offset(self, slot_id):
        return HEADER_SIZE + slot_id * SLOT_SIZE

    def free_space(self):
        slot_array_end = HEADER_SIZE + self.num_slots * SLOT_SIZE
        return self.free_space_offset - slot_array_end

    def insert_record(self, record_bytes):
        needed = len(record_bytes) + SLOT_SIZE
        if needed > self.free_space():
            raise ValueError("Page full")

        # write the record's bytes at the end, then move the boundary left
        self.free_space_offset -= len(record_bytes)
        self.buffer[self.free_space_offset : self.free_space_offset + len(record_bytes)] = record_bytes

        # append a new slot entry pointing at it
        slot_id = self.num_slots
        struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id),
                          self.free_space_offset, len(record_bytes))
        self.num_slots += 1

        self._write_header()
        return slot_id

    def get_record(self, slot_id):
        offset, length = struct.unpack_from(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id))
        if length == 0:
            return None   # tombstoned — see delete_record
        return bytes(self.buffer[offset : offset + length])

    def delete_record(self, slot_id):
        offset, _ = struct.unpack_from(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id))
        # zero the length but keep the slot entry itself — slot_id must stay stable
        struct.pack_into(SLOT_FORMAT, self.buffer, self._slot_offset(slot_id), offset, 0)

    def to_bytes(self):
        return bytes(self.buffer)

    @classmethod
    def from_bytes(cls, raw):
        page = cls.__new__(cls)
        page.buffer = bytearray(raw)
        page.num_slots, page.free_space_offset = struct.unpack_from(HEADER_FORMAT, page.buffer, 0)
        return page