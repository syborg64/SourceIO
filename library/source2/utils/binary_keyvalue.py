from enum import IntEnum, IntFlag
from io import BytesIO

import numpy as np

from ...utils.byte_io_mdl import ByteIO
from ...utils.pylib import LZ4ChainDecoder, lz4_decompress
from ..data_types.compiled_file_header import InfoBlock


def uncompress(compressed_data, compressed_size, decompressed_size):
    return lz4_decompress(compressed_data, compressed_size, decompressed_size)


class KVFlag(IntFlag):
    Nothing = 0
    Resource = 1
    DeferredResource = 2
    Unk = 16


class KVType(IntEnum):
    STRING_MULTI = 0  # STRING_MULTI doesn't have an ID
    NULL = 1
    BOOLEAN = 2
    INT64 = 3
    UINT64 = 4
    DOUBLE = 5
    STRING = 6
    BINARY_BLOB = 7
    ARRAY = 8
    OBJECT = 9
    ARRAY_TYPED = 10
    INT32 = 11
    UINT32 = 12
    BOOLEAN_TRUE = 13
    BOOLEAN_FALSE = 14
    INT64_ZERO = 15
    INT64_ONE = 16
    DOUBLE_ZERO = 17
    DOUBLE_ONE = 18
    UNK = 21


class BinaryKeyValue:
    KV3_ENCODING_BINARY_BLOCK_COMPRESSED = b"\x46\x1A\x79\x95\xBC\x95\x6C\x4F\xA7\x0B\x05\xBC\xA1\xB7\xDF\xD2"
    KV3_ENCODING_BINARY_UNCOMPRESSED = b"\x00\x05\x86\x1B\xD8\xF7\xC1\x40\xAD\x82\x75\xA4\x82\x67\xE7\x14"
    KV3_ENCODING_BINARY_BLOCK_LZ4 = b"\x8A\x34\x47\x68\xA1\x63\x5C\x4F\xA1\x97\x53\x80\x6F\xD9\xB1\x19"
    KV3_FORMAT_GENERIC = b"\x7C\x16\x12\x74\xE9\x06\x98\x46\xAF\xF2\xE6\x3E\xB5\x90\x37\xE7"
    VKV3_SIG = b'VKV\x03'
    KV3_v1_SIG = b'\x013VK'
    KV3_v2_SIG = b'\x023VK'

    KNOWN_SIGNATURES = (VKV3_SIG, KV3_v1_SIG, KV3_v2_SIG)

    indent = 0

    def __init__(self, block_info: InfoBlock = None):
        super().__init__()
        self.block_info = block_info
        self.strings = []
        self.types = np.array([])
        self.current_type = 0
        self.kv = []
        self.buffer = ByteIO()  # type: ByteIO

        self.byte_buffer = ByteIO()
        self.int_buffer = ByteIO()
        self.double_buffer = ByteIO()

        self.block_reader = ByteIO()
        self.block_sizes = []
        self.next_block_id = 0

    def read(self, reader: ByteIO):
        fourcc = reader.read(4)
        assert fourcc in self.KNOWN_SIGNATURES, 'Invalid KV Signature'
        if fourcc == self.KV3_v1_SIG:
            self.read_v1(reader)
        if fourcc == self.KV3_v2_SIG:
            self.read_v2(reader)
        elif fourcc == self.VKV3_SIG:
            self.read_v3(reader)

    def block_decompress(self, reader):
        flags = reader.read(4)
        if flags[3] & 0x80:
            self.buffer.write_bytes(reader.read(-1))
        working = True
        while reader.tell() != reader.size() and working:
            block_mask = reader.read_uint16()
            for i in range(16):
                if block_mask & (1 << i) > 0:
                    offset_and_size = reader.read_uint16()
                    offset = ((offset_and_size & 0xFFF0) >> 4) + 1
                    size = (offset_and_size & 0x000F) + 3
                    lookup_size = offset if offset < size else size

                    entry = self.buffer.tell()
                    self.buffer.seek(entry - offset)
                    data = self.buffer.read(lookup_size)
                    self.buffer.seek(entry)
                    while size > 0:
                        self.buffer.write_bytes(data[:lookup_size if lookup_size < size else size])
                        size -= lookup_size
                else:
                    data = reader.read_int8()
                    self.buffer.write_int8(data)
                if self.buffer.size() == (flags[2] << 16) + (flags[1] << 8) + flags[0]:
                    working = False
                    break
        self.buffer.seek(0)

    def decompress_lz4(self, reader):
        decompressed_size = reader.read_uint32()
        compressed_size = reader.size() - reader.tell()
        data = reader.read(-1)
        data = uncompress(data, compressed_size, decompressed_size)
        self.buffer.write_bytes(data)
        self.buffer.seek(0)

    def read_v1(self, reader: ByteIO):
        fmt = reader.read(16)
        assert fmt == self.KV3_FORMAT_GENERIC, 'Unrecognised KV3 Format'

        compression_method = reader.read_uint32()
        bin_blob_count = reader.read_uint32()
        int_count = reader.read_uint32()
        double_count = reader.read_uint32()
        if compression_method == 0:
            length = reader.read_uint32()
            self.buffer.write_bytes(reader.read(length))
        elif compression_method == 1:
            uncompressed_size = reader.read_uint32()
            compressed_size = self.block_info.size - reader.tell()
            data = reader.read(compressed_size)
            u_data = uncompress(data, compressed_size, uncompressed_size)
            assert len(u_data) == uncompressed_size, "Decompressed data size does not match expected size"
            self.buffer.write_bytes(u_data)
        else:
            raise NotImplementedError("Unknown KV3 compression method")

        self.buffer.seek(0)

        self.byte_buffer.write_bytes(self.buffer.read(bin_blob_count))
        self.byte_buffer.seek(0)

        if self.buffer.tell() % 4 != 0:
            self.buffer.seek(self.buffer.tell() + (4 - (self.buffer.tell() % 4)))

        self.int_buffer.write_bytes(self.buffer.read(int_count * 4))
        self.int_buffer.seek(0)

        if self.buffer.tell() % 8 != 0:
            self.buffer.seek(self.buffer.tell() + (8 - (self.buffer.tell() % 8)))

        self.double_buffer.write_bytes(self.buffer.read(double_count * 8))
        self.double_buffer.seek(0)

        for _ in range(self.int_buffer.read_uint32()):
            self.strings.append(self.buffer.read_ascii_string())

        types_len = self.buffer.size() - self.buffer.tell() - 4

        self.types = np.frombuffer(self.buffer.read(types_len), np.uint8)

        self.parse(self.buffer, self.kv, True)
        self.kv = self.kv[0]

        self.buffer.close()
        del self.buffer
        self.byte_buffer.close()
        del self.byte_buffer
        self.int_buffer.close()
        del self.int_buffer
        self.double_buffer.close()
        del self.double_buffer

    def read_v2(self, reader: ByteIO):
        fmt = reader.read(16)
        # assert fmt == self.KV3_FORMAT_GENERIC, 'Unrecognised KV3 Format'

        compression_method = reader.read_uint32()
        compression_dict_id = reader.read_uint16()
        compression_frame_size = reader.read_uint16()

        bin_blob_count = reader.read_uint32()
        int_count = reader.read_uint32()
        double_count = reader.read_uint32()

        string_and_types_buffer_size, b, c = reader.read_fmt('I2H')

        uncompressed_size = reader.read_uint32()
        compressed_size = reader.read_uint32()
        block_count = reader.read_uint32()
        block_total_size = reader.read_uint32()

        if compression_method == 0:
            if compression_dict_id != 0:
                raise NotImplementedError('Unknown compression method in KV3 v2 block')
            if compression_frame_size != 0:
                raise NotImplementedError('Unknown compression method in KV3 v2 block')
            self.buffer.write_bytes(reader.read(compressed_size))
        elif compression_method == 1:

            if compression_dict_id != 0:
                raise NotImplementedError('Unknown compression method in KV3 v2 block')

            if compression_frame_size != 16384:
                raise NotImplementedError('Unknown compression method in KV3 v2 block')

            data = reader.read(compressed_size)
            u_data = uncompress(data, compressed_size, uncompressed_size)
            assert len(u_data) == uncompressed_size, "Decompressed data size does not match expected size"
            self.buffer.write_bytes(u_data)
            del u_data, data
        elif compression_method == 2:
            from ...utils.thirdparty.zstandard import ZstdDecompressor
            data = reader.read(compressed_size)
            decompressor = ZstdDecompressor()
            tmp = BytesIO()
            decompressor.copy_stream(BytesIO(data), tmp, compressed_size, uncompressed_size)
            tmp.seek(0)
            u_data = tmp.read()
            assert len(
                u_data) == uncompressed_size + block_total_size, "Decompressed data size does not match expected size"
            self.buffer.write_bytes(u_data)
            del u_data, data
        else:
            raise NotImplementedError(f"Unknown {compression_method} KV3 compression method")

        self.buffer.seek(0)

        self.byte_buffer.write_bytes(self.buffer.read(bin_blob_count))
        self.byte_buffer.seek(0)

        if self.buffer.tell() % 4 != 0:
            self.buffer.seek(self.buffer.tell() + (4 - (self.buffer.tell() % 4)))

        self.int_buffer.write_bytes(self.buffer.read(int_count * 4))
        self.int_buffer.seek(0)

        if self.buffer.tell() % 8 != 0:
            self.buffer.seek(self.buffer.tell() + (8 - (self.buffer.tell() % 8)))

        self.double_buffer.write_bytes(self.buffer.read(double_count * 8))
        self.double_buffer.seek(0)

        string_start = self.buffer.tell()

        for _ in range(self.int_buffer.read_uint32()):
            self.strings.append(self.buffer.read_ascii_string())

        types_len = string_and_types_buffer_size - (self.buffer.tell() - string_start)
        self.types = np.frombuffer(self.buffer.read(types_len), np.uint8)
        del types_len, string_start, string_and_types_buffer_size, b, c
        if block_count == 0:
            assert self.buffer.read_uint32() == 0xFFEEDD00, 'Invalid terminator'
            self.parse(self.buffer, self.kv, True)
            self.kv = self.kv[0]
        else:
            self.block_sizes = [self.buffer.read_uint32() for _ in range(block_count)]
            assert self.buffer.read_uint32() == 0xFFEEDD00, 'Invalid terminator'

            block_data = bytearray()

            if compression_method == 0:
                for uncompressed_block_size in self.block_sizes:
                    block_data += reader.read(uncompressed_block_size)
            elif compression_method == 1:
                cd = LZ4ChainDecoder(block_total_size, 0)
                for uncompressed_block_size in self.block_sizes:
                    compressed_block_size = self.buffer.read_uint16()
                    block_data += cd.decompress(reader.read(compressed_block_size), uncompressed_block_size)
            elif compression_method == 2:
                block_data += self.buffer.read()
            else:
                raise NotImplementedError(f"Unknown {compression_method} KV3 compression method")

            self.block_reader.write_bytes(block_data)
            self.block_reader.seek(0)
            self.parse(self.buffer, self.kv, True)
            self.kv = self.kv[0]

        self.buffer.close()
        del self.buffer
        self.byte_buffer.close()
        del self.byte_buffer
        self.int_buffer.close()
        del self.int_buffer
        self.double_buffer.close()
        del self.double_buffer

    def read_v3(self, reader):
        encoding = reader.read(16)
        assert encoding in (
            self.KV3_ENCODING_BINARY_BLOCK_COMPRESSED,
            self.KV3_ENCODING_BINARY_BLOCK_LZ4,
            self.KV3_ENCODING_BINARY_UNCOMPRESSED,
        ), 'Unrecognized KV3 Encoding'

        fmt = reader.read(16)

        # assert fmt == self.KV3_FORMAT_GENERIC, 'Unrecognised KV3 Format'
        if encoding == self.KV3_ENCODING_BINARY_BLOCK_COMPRESSED:
            self.block_decompress(reader)
        elif encoding == self.KV3_ENCODING_BINARY_BLOCK_LZ4:
            self.decompress_lz4(reader)
        elif encoding == self.KV3_ENCODING_BINARY_UNCOMPRESSED:
            self.buffer.write_bytes(reader.read(-1))
            self.buffer.seek(0)
        string_count = self.buffer.read_uint32()
        for _ in range(string_count):
            self.strings.append(self.buffer.read_ascii_string())
        self.int_buffer = self.buffer
        self.double_buffer = self.buffer
        self.byte_buffer = self.buffer
        self.parse(self.buffer, self.kv, True)
        assert len(self.kv) == 1, "Never yet seen that state of vkv3 v1"
        self.kv = self.kv[0]
        self.buffer.close()
        del self.buffer

    def read_type(self, reader: ByteIO):
        if self.types.shape[0] > 0:
            data_type = self.types[self.current_type]
            self.current_type += 1
        else:
            data_type = reader.read_int8()

        flag_info = KVFlag.Nothing
        if data_type & 0x80:
            data_type &= 0x7F
            if self.types.shape[0] > 0:
                flag_info = KVFlag(self.types[self.current_type])
                self.current_type += 1
            else:
                flag_info = KVFlag(reader.read_int8())
        return KVType(data_type), flag_info

    def parse(self, reader: ByteIO, parent=None, in_array=False):
        name = None
        if not in_array:
            str_id = self.int_buffer.read_int32()
            name = self.strings[str_id] if str_id != -1 else ""
        data_type, flag_info = self.read_type(reader)
        self.read_value(name, reader, data_type, parent, in_array)

    def read_value(self, name, reader: ByteIO, data_type: KVType, parent, is_array=False):
        def add(v):
            if not is_array:
                parent.update({name: v})
            else:
                parent.append(v)

        if data_type == KVType.NULL:
            add(None)
            return
        elif data_type == KVType.DOUBLE:
            add(self.double_buffer.read_double())
            return
        elif data_type == KVType.BOOLEAN:
            add(self.byte_buffer.read_int8() == 1)
            return
        elif data_type == KVType.BOOLEAN_TRUE:
            add(True)
            return
        elif data_type == KVType.BOOLEAN_FALSE:
            add(False)
            return
        elif data_type == KVType.INT64:
            add(self.double_buffer.read_int64())
            return
        elif data_type == KVType.UINT64:
            add(self.double_buffer.read_uint64())
            return
        elif data_type == KVType.DOUBLE_ZERO:
            add(0.0)
            return
        elif data_type == KVType.INT64_ZERO:
            add(0)
            return
        elif data_type == KVType.INT64_ONE:
            add(1)
            return
        elif data_type == KVType.DOUBLE_ONE:
            add(1.0)
            return
        elif data_type == KVType.INT32:
            add(self.int_buffer.read_int32())
            return
        elif data_type == KVType.UINT32:
            add(self.int_buffer.read_uint32())
            return
        elif data_type == KVType.STRING:
            string_id = self.int_buffer.read_int32()
            if string_id == -1:
                add(None)
            else:
                add(self.strings[string_id])
            return
        elif data_type == KVType.ARRAY:
            size = self.int_buffer.read_uint32()
            arr = []
            for _ in range(size):
                self.parse(reader, arr, True)
            add(arr)
            return
        elif data_type == KVType.OBJECT:
            size = self.int_buffer.read_uint32()
            tmp = {}
            for _ in range(size):
                self.parse(reader, tmp, False)
            add(tmp)
            if not parent:
                parent = tmp
        elif data_type == KVType.ARRAY_TYPED:
            t_array_size = self.int_buffer.read_uint32()
            sub_type, sub_flag = self.read_type(reader)
            tmp = []
            for _ in range(t_array_size):
                self.read_value(name, reader, sub_type, tmp, True)

            if sub_type in (KVType.DOUBLE, KVType.DOUBLE_ONE, KVType.DOUBLE_ZERO):
                tmp = np.array(tmp, dtype=np.float64)
            add(tmp)
        elif data_type == KVType.BINARY_BLOB:
            if self.block_reader.size() != 0:
                data = self.block_reader.read(self.block_sizes[self.next_block_id])
                self.next_block_id += 1
                add(data)
            elif self.block_reader.size() == 0 and self.block_sizes:
                add('ERROR')
            else:
                size = self.int_buffer.read_uint32()
                add(self.byte_buffer.read(size))
            return
        else:
            raise NotImplementedError("Unknown KVType.{}".format(data_type.name))

        return parent
