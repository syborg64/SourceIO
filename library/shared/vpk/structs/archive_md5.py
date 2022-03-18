from ....utils.byte_io_mdl import ByteIO


class ArchiveMD5Entry:

    def __init__(self):
        self.archive_id = 0
        self.offset = 0
        self.size = 0
        self.crc32 = 0xBAADF00D

    def read(self, reader: ByteIO):
        (self.archive_id, self.offset, self.size) = reader.read_fmt('3I')
        self.crc32 = reader.read(16)

    def __str__(self):
        return f'ArchiveMD5Entry(arch_id: {self.archive_id} size:{self.size})'
