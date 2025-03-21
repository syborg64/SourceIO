from pathlib import Path
from typing import Dict

from .source2_base import Source2DetectorBase
from ..content_provider_base import ContentProviderBase, ContentDetectorBase
from ..source2_content_provider import GameinfoContentProvider
from ..vpk_sub_manager import VPKContentProvider
from ...utilities.path_utilities import backwalk_file_resolver
from ..hla_content_provider import HLAAddonProvider


class RobotRepairDetector(Source2DetectorBase):

    @classmethod
    def scan(cls, path: Path) -> Dict[str, ContentProviderBase]:
        game_root = None
        p2imp_folder = backwalk_file_resolver(path, 'portal2_imported')
        if p2imp_folder is not None:
            game_root = p2imp_folder.parent
        if game_root is None:
            return {}
        content_providers = {}
        cls.recursive_traversal(game_root, 'vr', content_providers)
        return content_providers
