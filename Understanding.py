import struct
FORMAT = "I20sI50s"
RECORD_SIZE = struct.calcsize(FORMAT)
records = [(1,b"Siddhartha", 984012345, b"siddhartha2gmail.com")]
with open ("manxe.db", "wb") as f:
    for rid, name, number, email in records:
        f.write (struct.pack(FORMAT, rid, name.ljust(20,b"\x00"), number, email.ljust(50,b"\x00")))
with open("manxe.db", "rb") as f:
    while chunk := f.read(RECORD_SIZE):
        rid, name, number, email =  struct.unpack(FORMAT, chunk)
        print (rid,name.rstrip (b"\x00").decode(), number, email.rstrip(b"\x00").decode())