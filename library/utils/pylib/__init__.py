import platform
from ctypes import (c_bool, c_char_p, c_int, c_int32, c_size_t, c_uint32,
                    c_void_p, cdll, POINTER, Structure, sizeof, create_string_buffer, pointer, c_ubyte, cast)
from enum import IntEnum, auto
from pathlib import Path
from typing import Optional

platform_info = platform.uname()


class UnsupportedSystem(Exception):
    pass


class DecompressStatus(IntEnum):
    NotFinished = 0
    HasMoreOutput = 1
    NeedsMoreInput = 2
    Success = 3
    Failure = 4
    DestinationBufferTooSmall = 5
    ExpectedMoreRawBytes = 6
    BadCode = 7
    Adler32 = 8
    BadRawBlock = 9
    BadCompBlockSyncCheck = 10
    BadZlibHeader = 11
    NeedSeedBytes = 12
    BadSeedBytes = 13
    BadSyncBlock = 14
    InvalidParameter = 15


class DecompressionParameters(Structure):
    _fields_ = [
        ('m_struct_size', c_uint32),
        ('m_dict_size_log2', c_uint32),
        ('m_decompress_flags', c_uint32),
        ('m_num_seed_bytes', c_uint32),
        ('m_pSeed_bytes', c_char_p),
    ]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.m_struct_size = sizeof(self)


def pointer_to_array(poiter, size, c_type=c_ubyte):
    return cast(poiter, POINTER(c_type * size))


pylib_path: Optional[Path] = Path(__file__).parent
if platform_info.system == "Windows":
    pylib_path /= "win/pylib.dll"

elif platform_info.system == 'Linux':
    pylib_path /= "unix/pylib.so"

elif platform_info.system == 'Darwin' and platform_info.machine == "arm64":
    pylib_path /= "macos_m1/pylib.dylib"
elif platform_info.system == 'Darwin' and platform_info.machine == "x86_64":
    pylib_path /= "macos_x86/pylib.dylib"
else:
    raise UnsupportedSystem(f'System {platform_info} not suppported')

assert pylib_path.exists()


def load_dll():
    return cdll.LoadLibrary(pylib_path.as_posix())


LIB = load_dll()

# size_t zstd_compress_bound(size_t size)
_zstd_compress_bound = LIB.zstd_compress_bound
_zstd_compress_bound.argtypes = [c_size_t]
_zstd_compress_bound.restype = c_size_t

# size_t zstd_decompress(char *src, size_t src_size, char *dst, size_t dst_size)
_zstd_decompress = LIB.zstd_decompress
_zstd_decompress.argtypes = [c_char_p, c_size_t, c_char_p, c_size_t]
_zstd_decompress.restype = c_size_t

# size_t zstd_compress(char *src, size_t src_size, char *dst, size_t dst_size)
_zstd_compress = LIB.zstd_compress
_zstd_compress.argtypes = [c_char_p, c_size_t, c_char_p, c_size_t]
_zstd_compress.restype = c_size_t

# size_t zstd_compress_stream(char *src, size_t src_size, char *dst, size_t dst_size)
_zstd_compress_stream = LIB.zstd_compress_stream
_zstd_compress_stream.argtypes = [c_char_p, c_size_t, c_char_p, c_size_t]
_zstd_compress_stream.restype = c_size_t

# size_t zstd_decompress_stream(char *src, size_t src_size, char *dst, size_t dst_size)
_zstd_decompress_stream = LIB.zstd_decompress_stream
_zstd_decompress_stream.argtypes = [c_char_p, c_size_t, c_char_p, c_size_t]
_zstd_decompress_stream.restype = c_size_t

# int lz4_decompress(char *src, int src_size, char *dst, int dst_size)
_lz4_decompress = LIB.lz4_decompress
_lz4_decompress.argtypes = [c_char_p, c_int, c_char_p, c_int]
_lz4_decompress.restype = c_int

# int lz4_compress(char *src, int src_size, char *dst, int dst_size)
_lz4_compress = LIB.lz4_compress
_lz4_compress.argtypes = [c_char_p, c_int, c_char_p, c_int]
_lz4_compress.restype = c_int

# LZ4ChainDecoder *LZ4ChainDecoder_new()
_LZ4ChainDecoder_new = LIB.LZ4ChainDecoder_new
_LZ4ChainDecoder_new.argtypes = []
_LZ4ChainDecoder_new.restype = c_void_p

# int LZ4ChainDecoder_init(LZ4ChainDecoder *self, int block_size, int extra_blocks)
_LZ4ChainDecoder_init = LIB.LZ4ChainDecoder_init
_LZ4ChainDecoder_init.argtypes = [c_void_p, c_int, c_int]
_LZ4ChainDecoder_init.restype = c_int

# bool LZ4ChainDecoder_decompress(LZ4ChainDecoder *self, char *src, size_t data_size, char *dst, size_t decompressed_size)
_LZ4ChainDecoder_decompress = LIB.LZ4ChainDecoder_decompress
_LZ4ChainDecoder_decompress.argtypes = [c_void_p, c_char_p, c_size_t, c_char_p, c_size_t]
_LZ4ChainDecoder_decompress.restype = c_bool

# void LZ4ChainDecoder_dealloc(LZ4ChainDecoder *self)
_LZ4ChainDecoder_dealloc = LIB.LZ4ChainDecoder_dealloc
_LZ4ChainDecoder_dealloc.argtypes = [c_void_p]
_LZ4ChainDecoder_dealloc.restype = None

# bool decode_index_buffer(char *src, size_t src_size, char *dst, size_t dst_size, int32_t index_size, int32_t index_count)
_decode_index_buffer = LIB.decode_index_buffer
_decode_index_buffer.argtypes = [c_char_p, c_size_t, c_char_p, c_size_t, c_int32, c_int32]
_decode_index_buffer.restype = c_bool

# bool decode_vertex_buffer(char *src, size_t src_size, char *dst, size_t dst_size, int32_t vertex_size, int32_t vertex_count)
_decode_vertex_buffer = LIB.decode_vertex_buffer
_decode_vertex_buffer.argtypes = [c_char_p, c_size_t, c_char_p, c_size_t, c_int32, c_int32]
_decode_vertex_buffer.restype = c_bool

# dll_export bool image_decompress(char *src, size_t src_size, char *dst, size_t dst_size, int32_t width,
#                                 int32_t height, uint32_t input_fmt, uint32_t output_fmt, uint32_t flip)

_image_decompress = LIB.image_decompress
_image_decompress.argtypes = [c_char_p, c_size_t, c_char_p, c_size_t, c_int32, c_int32, c_uint32, c_uint32, c_uint32]
_image_decompress.restype = c_bool

_get_version = LIB.lzham_get_version
_get_version.argtypes = []
_get_version.restype = c_uint32

_compress_init = LIB.lzham_compress_init
_compress_init.argtypes = [c_char_p]
_compress_init.restype = POINTER(c_uint32)

_compress_reinit = LIB.lzham_compress_reinit
_compress_reinit.argtypes = [POINTER(c_uint32)]
_compress_reinit.restype = POINTER(c_uint32)

_compress = LIB.lzham_compress
_compress.argtypes = [POINTER(c_uint32), c_char_p, POINTER(c_uint32), c_char_p, POINTER(c_uint32), c_uint32]
_compress.restype = c_uint32

_compress2 = LIB.lzham_compress2
_compress2.argtypes = [POINTER(c_uint32), c_char_p, POINTER(c_uint32), c_char_p, POINTER(c_uint32), c_uint32]
_compress2.restype = c_uint32

_compress_memory = LIB.lzham_compress_memory
_compress_memory.argtypes = [c_char_p, c_char_p, POINTER(c_uint32), c_char_p, c_uint32, POINTER(c_uint32)]
_compress_memory.restype = c_uint32

_compress_deinit = LIB.lzham_compress_deinit
_compress_deinit.argtypes = [POINTER(c_uint32)]
_compress_deinit.restype = c_uint32

_decompress_init = LIB.lzham_decompress_init
_decompress_init.argtypes = [POINTER(DecompressionParameters)]
_decompress_init.restype = POINTER(c_uint32)

_decompress_reinit = LIB.lzham_decompress_reinit
_decompress_reinit.argtypes = [POINTER(c_uint32), POINTER(c_uint32)]
_decompress_reinit.restype = POINTER(c_uint32)

_decompress = LIB.lzham_decompress
_decompress.argtypes = [POINTER(c_uint32), c_char_p, POINTER(c_uint32), c_char_p, POINTER(c_uint32), c_uint32]
_decompress.restype = POINTER(c_uint32)

_decompress_memory = LIB.lzham_decompress_memory
_decompress_memory.argtypes = [POINTER(DecompressionParameters), c_char_p, POINTER(c_uint32), c_char_p,
                               POINTER(c_uint32),
                               POINTER(c_uint32)]
_decompress_memory.restype = DecompressStatus


def zstd_decompress(src: bytes, compressed_size, decompressed_size):
    dst = bytes(decompressed_size)
    assert len(src) == compressed_size
    res = _zstd_decompress(src, compressed_size, dst, decompressed_size)
    if res < 0:
        raise BufferError(f"Failed to decompress LZ4 data:{res}")
    return dst


def zstd_compress(src: bytes):
    src_size = len(src)
    dst = bytes(src_size)
    assert len(src) == src_size
    res = _zstd_compress(src, src_size, dst, src_size)
    if res < 0:
        raise BufferError(f"Failed to compress LZ4 data:{res}")
    return dst[:res]


def zstd_decompress_stream(src: bytes, compressed_size, decompressed_size):
    dst = bytes(decompressed_size)
    assert len(src) == compressed_size
    res = _zstd_decompress_stream(src, compressed_size, dst, decompressed_size)
    if res < 0:
        raise BufferError(f"Failed to decompress LZ4 data:{res}")
    return dst


def zstd_compress_stream(src: bytes):
    src_size = len(src)
    assert len(src) == src_size
    possible_dst_size = _zstd_compress_bound(src_size)
    dst = bytes(possible_dst_size)
    res = _zstd_compress_stream(src, src_size, dst, possible_dst_size)
    if res < 0:
        raise BufferError(f"Failed to compress LZ4 data:{res}")
    return dst[:res]


def lz4_decompress(src: bytes, compressed_size, decompressed_size):
    dst = bytes(decompressed_size)
    assert len(src) == compressed_size
    res = _lz4_decompress(src, compressed_size, dst, decompressed_size)
    if res < 0:
        raise BufferError(f"Failed to decompress LZ4 data:{res}")
    return dst


def lz4_compress(src: bytes):
    src_size = len(src)
    dst = bytes(src_size)
    assert len(src) == src_size
    res = _lz4_decompress(src, src_size, dst, src_size)
    if res < 0:
        raise BufferError(f"Failed to compress LZ4 data:{res}")
    return dst[:res]


class LZ4ChainDecoder:
    def __init__(self, block_size: int, extra_blocks: int):
        self._handle: c_void_p = _LZ4ChainDecoder_new()
        _LZ4ChainDecoder_init(self._handle, block_size, extra_blocks)

    def __del__(self):
        _LZ4ChainDecoder_dealloc(self._handle)

    def decompress(self, src: bytes, decompressed_size: int):
        dst = bytes(decompressed_size)
        res = _LZ4ChainDecoder_decompress(self._handle, src, len(src), dst, decompressed_size)
        if not res:
            raise BufferError(f"Failed to decompress LZ4Chain data")
        return dst


def decode_index_buffer(src: bytes, index_size: int, index_count: int):
    dst = bytes(index_size * index_count)
    _decode_index_buffer(src, len(src), dst, len(dst), index_size, index_count)
    return dst


def decode_vertex_buffer(src: bytes, vertex_size: int, vertex_count: int):
    dst = bytes(vertex_size * vertex_count)
    _decode_vertex_buffer(src, len(src), dst, len(dst), vertex_size, vertex_count)
    return dst


class ImageFormat(IntEnum):
    RGBA8 = 0x00000334
    RGBX16F = 0x00002721
    BC1 = 0x1000320
    BC1A = 0x2000334
    BC2 = 0x3800334
    BC3 = 0x4800334
    BC4 = 0x5000000
    ATI1 = BC4
    BC5 = 0x7800110
    ATI2 = BC5
    BC6U = 0x9802721
    BC6S = 0xA803721
    BC7 = 0xB800334
    ETC1 = 0xC000320
    ETC2 = 0xD000320


def decompress_image(src: bytes, width: int, height: int, src_format: ImageFormat, dst_format: ImageFormat, flip: bool):
    assert dst_format in (ImageFormat.RGBA8, ImageFormat.RGBX16F)
    pixel_size = 4
    if dst_format == ImageFormat.RGBX16F:
        pixel_size = 8
    dst = bytes(width * height * pixel_size)
    if not _image_decompress(src, len(src), dst, len(dst), width, height, src_format.value, dst_format.value, flip):
        return None
    return dst


class LZHAM:
    def __init__(self):
        self.decompress_handle = POINTER(c_uint32)()

    def version(self):
        return _get_version()

    def init_decompress(self, dict_size=15):
        params = DecompressionParameters()
        params.m_dict_size_log2 = dict_size
        self.decompress_handle = _decompress_init(params)
        assert self.decompress_handle.contents.value != 0

    def reinit_decompress(self, dict_size=15):
        params = DecompressionParameters()
        params.m_dict_size_log2 = dict_size
        self.decompress_handle = _compress_reinit(self.decompress_handle, params)

    @classmethod
    def decompress_memory(cls, compressed_data, decompressed_size, dict_size=15, flags=0):
        compressed_size = len(compressed_data)
        compressed_ptr = create_string_buffer(compressed_data)
        decompressed_ptr = create_string_buffer(decompressed_size)
        compressed_size_ptr = pointer(c_uint32(compressed_size))
        decompressed_size_ptr = pointer(c_uint32(decompressed_size))
        decompressed_params = DecompressionParameters()
        decompressed_params.m_dict_size_log2 = dict_size
        decompressed_params.m_decompress_flags = flags
        adler_prt = pointer(c_uint32(0))
        result = _decompress_memory(decompressed_params,
                                    decompressed_ptr, decompressed_size_ptr,
                                    compressed_ptr, compressed_size_ptr,
                                    adler_prt)
        if result == DecompressStatus.Success:
            return pointer_to_array(decompressed_ptr, decompressed_size_ptr.contents.value).contents
        else:
            raise Exception(f'LZHAM decompression error: {result.name}')
