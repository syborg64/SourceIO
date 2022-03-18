from io import BytesIO
from pathlib import Path
from typing import Union

from ....shared.content_providers.content_provider_base import ContentProviderBase
from .. import Lump, lump_tag
import zipfile


@lump_tag(40, 'LUMP_PAK')
class PakLump(Lump, ContentProviderBase):

    def find_path(self, filepath: Union[str, Path]):
        pass

    def __init__(self, bsp, lump_id):
        super().__init__(bsp, lump_id)
        self.filepath = self._bsp.filepath
        self.zip_file: zipfile.ZipFile = None
        self._filename_cache = {}

    def parse(self):
        if self.zip_file is None:
            self.reader.seek(0)
            zip_data = BytesIO(self.reader.read())
            self.zip_file = zipfile.ZipFile(zip_data)
            self._filename_cache = {a.lower(): a for a in self.zip_file.NameToInfo}
        return self

    def find_file(self, filepath: Union[str, Path], additional_dir=None, extension=None):
        filepath = Path(str(filepath).strip("\\/"))

        new_filepath = filepath
        if additional_dir:
            new_filepath = Path(additional_dir, new_filepath)
        if extension:
            new_filepath = new_filepath.with_suffix(extension)
        new_filepath = str(new_filepath.as_posix()).lower()
        new_filepath = self._filename_cache.get(new_filepath, None)

        cached_file = self.get_from_cache(new_filepath)
        if cached_file:
            return cached_file

        if new_filepath is not None:
            return self.cache_file(new_filepath, BytesIO(self.zip_file.open(new_filepath, 'r').read()))
        return None

    @property
    def steam_id(self):
        return -1
