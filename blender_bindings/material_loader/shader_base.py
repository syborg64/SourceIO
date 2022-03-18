from pathlib import Path
import sys
from typing import Optional, Tuple

import bpy
import numpy as np

from .node_arranger import nodes_iterate
from ..utils.utils import append_blend
from ...logger import SLoggingManager


class Nodes:
    ShaderNodeAddShader = 'ShaderNodeAddShader'
    ShaderNodeAmbientOcclusion = 'ShaderNodeAmbientOcclusion'
    ShaderNodeAttribute = 'ShaderNodeAttribute'
    ShaderNodeBackground = 'ShaderNodeBackground'
    ShaderNodeBevel = 'ShaderNodeBevel'
    ShaderNodeBlackbody = 'ShaderNodeBlackbody'
    ShaderNodeBrightContrast = 'ShaderNodeBrightContrast'
    ShaderNodeBsdfAnisotropic = 'ShaderNodeBsdfAnisotropic'
    ShaderNodeBsdfDiffuse = 'ShaderNodeBsdfDiffuse'
    ShaderNodeBsdfGlass = 'ShaderNodeBsdfGlass'
    ShaderNodeBsdfGlossy = 'ShaderNodeBsdfGlossy'
    ShaderNodeBsdfHair = 'ShaderNodeBsdfHair'
    ShaderNodeBsdfHairPrincipled = 'ShaderNodeBsdfHairPrincipled'
    ShaderNodeBsdfPrincipled = 'ShaderNodeBsdfPrincipled'
    ShaderNodeBsdfRefraction = 'ShaderNodeBsdfRefraction'
    ShaderNodeBsdfToon = 'ShaderNodeBsdfToon'
    ShaderNodeBsdfTranslucent = 'ShaderNodeBsdfTranslucent'
    ShaderNodeBsdfTransparent = 'ShaderNodeBsdfTransparent'
    ShaderNodeBsdfVelvet = 'ShaderNodeBsdfVelvet'
    ShaderNodeBump = 'ShaderNodeBump'
    ShaderNodeCameraData = 'ShaderNodeCameraData'
    ShaderNodeClamp = 'ShaderNodeClamp'
    ShaderNodeCombineHSV = 'ShaderNodeCombineHSV'
    ShaderNodeCombineRGB = 'ShaderNodeCombineRGB'
    ShaderNodeCombineXYZ = 'ShaderNodeCombineXYZ'
    ShaderNodeCustomGroup = 'ShaderNodeCustomGroup'
    ShaderNodeDisplacement = 'ShaderNodeDisplacement'
    ShaderNodeEeveeSpecular = 'ShaderNodeEeveeSpecular'
    ShaderNodeEmission = 'ShaderNodeEmission'
    ShaderNodeFresnel = 'ShaderNodeFresnel'
    ShaderNodeGamma = 'ShaderNodeGamma'
    ShaderNodeGroup = 'ShaderNodeGroup'
    ShaderNodeHairInfo = 'ShaderNodeHairInfo'
    ShaderNodeHoldout = 'ShaderNodeHoldout'
    ShaderNodeHueSaturation = 'ShaderNodeHueSaturation'
    ShaderNodeInvert = 'ShaderNodeInvert'
    ShaderNodeLayerWeight = 'ShaderNodeLayerWeight'
    ShaderNodeLightFalloff = 'ShaderNodeLightFalloff'
    ShaderNodeLightPath = 'ShaderNodeLightPath'
    ShaderNodeMapRange = 'ShaderNodeMapRange'
    ShaderNodeMapping = 'ShaderNodeMapping'
    ShaderNodeMath = 'ShaderNodeMath'
    ShaderNodeMixRGB = 'ShaderNodeMixRGB'
    ShaderNodeMixShader = 'ShaderNodeMixShader'
    ShaderNodeNewGeometry = 'ShaderNodeNewGeometry'
    ShaderNodeNormal = 'ShaderNodeNormal'
    ShaderNodeNormalMap = 'ShaderNodeNormalMap'
    ShaderNodeObjectInfo = 'ShaderNodeObjectInfo'
    ShaderNodeOutputAOV = 'ShaderNodeOutputAOV'
    ShaderNodeOutputLight = 'ShaderNodeOutputLight'
    ShaderNodeOutputLineStyle = 'ShaderNodeOutputLineStyle'
    ShaderNodeOutputMaterial = 'ShaderNodeOutputMaterial'
    ShaderNodeOutputWorld = 'ShaderNodeOutputWorld'
    ShaderNodeParticleInfo = 'ShaderNodeParticleInfo'
    ShaderNodeRGB = 'ShaderNodeRGB'
    ShaderNodeRGBCurve = 'ShaderNodeRGBCurve'
    ShaderNodeRGBToBW = 'ShaderNodeRGBToBW'
    ShaderNodeScript = 'ShaderNodeScript'
    ShaderNodeSeparateHSV = 'ShaderNodeSeparateHSV'
    ShaderNodeSeparateRGB = 'ShaderNodeSeparateRGB'
    ShaderNodeSeparateXYZ = 'ShaderNodeSeparateXYZ'
    ShaderNodeShaderToRGB = 'ShaderNodeShaderToRGB'
    ShaderNodeSqueeze = 'ShaderNodeSqueeze'
    ShaderNodeSubsurfaceScattering = 'ShaderNodeSubsurfaceScattering'
    ShaderNodeTangent = 'ShaderNodeTangent'
    ShaderNodeTexBrick = 'ShaderNodeTexBrick'
    ShaderNodeTexChecker = 'ShaderNodeTexChecker'
    ShaderNodeTexCoord = 'ShaderNodeTexCoord'
    ShaderNodeTexEnvironment = 'ShaderNodeTexEnvironment'
    ShaderNodeTexGradient = 'ShaderNodeTexGradient'
    ShaderNodeTexIES = 'ShaderNodeTexIES'
    ShaderNodeTexImage = 'ShaderNodeTexImage'
    ShaderNodeTexMagic = 'ShaderNodeTexMagic'
    ShaderNodeTexMusgrave = 'ShaderNodeTexMusgrave'
    ShaderNodeTexNoise = 'ShaderNodeTexNoise'
    ShaderNodeTexPointDensity = 'ShaderNodeTexPointDensity'
    ShaderNodeTexSky = 'ShaderNodeTexSky'
    ShaderNodeTexVoronoi = 'ShaderNodeTexVoronoi'
    ShaderNodeTexWave = 'ShaderNodeTexWave'
    ShaderNodeTexWhiteNoise = 'ShaderNodeTexWhiteNoise'
    ShaderNodeUVAlongStroke = 'ShaderNodeUVAlongStroke'
    ShaderNodeUVMap = 'ShaderNodeUVMap'
    ShaderNodeValToRGB = 'ShaderNodeValToRGB'
    ShaderNodeValue = 'ShaderNodeValue'
    ShaderNodeVectorCurve = 'ShaderNodeVectorCurve'
    ShaderNodeVectorDisplacement = 'ShaderNodeVectorDisplacement'
    ShaderNodeVectorMath = 'ShaderNodeVectorMath'
    ShaderNodeVectorRotate = 'ShaderNodeVectorRotate'
    ShaderNodeVectorTransform = 'ShaderNodeVectorTransform'
    ShaderNodeVertexColor = 'ShaderNodeVertexColor'
    ShaderNodeVolumeAbsorption = 'ShaderNodeVolumeAbsorption'
    ShaderNodeVolumeInfo = 'ShaderNodeVolumeInfo'
    ShaderNodeVolumePrincipled = 'ShaderNodeVolumePrincipled'
    ShaderNodeVolumeScatter = 'ShaderNodeVolumeScatter'
    ShaderNodeWavelength = 'ShaderNodeWavelength'
    ShaderNodeWireframe = 'ShaderNodeWireframe'


log_manager = SLoggingManager()
logger = log_manager.get_logger('MaterialLoader')


class ShaderBase:
    SHADER: str = "Unknown"
    use_bvlg_status = True

    @classmethod
    def use_bvlg(cls, status):
        cls.use_bvlg_status = status

    @staticmethod
    def load_bvlg_nodes():
        if "VertexLitGeneric" not in bpy.data.node_groups:
            current_path = Path(__file__).parent.parent
            asset_path = current_path / 'assets' / "sycreation-s-default.blend"
            append_blend(str(asset_path), "node_groups")

    @staticmethod
    def ensure_length(array: list, length, filler):
        if len(array) < length:
            array.extend([filler] * (length - len(array)))
            return array
        elif len(array) > length:
            return array[:length]
        return array

    @classmethod
    def all_subclasses(cls):
        return set(cls.__subclasses__()).union([s for c in cls.__subclasses__() for s in c.all_subclasses()])

    def __init__(self):
        self.logger = log_manager.get_logger(f'Shaders::{self.SHADER}')
        self.bpy_material: bpy.types.Material = None
        self.load_bvlg_nodes()
        self.do_arrange = True

    @staticmethod
    def get_missing_texture(texture_name: str, fill_color: tuple = (1.0, 1.0, 1.0, 1.0)):
        assert len(fill_color) == 4, 'Fill color should be in RGBA format'
        if bpy.data.images.get(texture_name, None):
            return bpy.data.images.get(texture_name)
        else:
            image = bpy.data.images.new(texture_name, width=512, height=512, alpha=False)
            image_data = np.full((512 * 512, 4), fill_color, np.float32).flatten()
            if bpy.app.version > (2, 83, 0):
                image.pixels.foreach_set(image_data)
            else:
                image.pixels[:] = image_data
            return image

    def load_texture(self, texture_name, texture_path) -> Optional[bpy.types.Image]:
        pass

    @staticmethod
    def make_texture(texture_name, texture_dimm, texture_data, raw_texture=False):
        image = bpy.data.images.new(texture_name, width=texture_dimm[0], height=texture_dimm[1], alpha=True)
        image.alpha_mode = 'CHANNEL_PACKED'
        image.file_format = 'TARGA'
        if bpy.app.version > (2, 83, 0):
            image.pixels.foreach_set(texture_data.flatten().tolist())
        else:
            image.pixels[:] = texture_data.flatten().tolist()
        image.pack()
        if raw_texture:
            image.colorspace_settings.is_data = True
            image.colorspace_settings.name = 'Non-Color'
        return image

    @staticmethod
    def split_to_channels(image):
        if bpy.app.version > (2, 83, 0):
            buffer = np.zeros(image.size[0] * image.size[1] * 4, np.float32)
            image.pixels.foreach_get(buffer)
        else:
            buffer = np.array(image.pixels[:])
        return buffer[0::4], buffer[1::4], buffer[2::4], buffer[3::4],

    def load_texture_or_default(self, file: str, default_color: tuple = (1.0, 1.0, 1.0, 1.0)):
        texture_name = Path(file).stem
        texture = self.load_texture(texture_name, file)
        return texture or self.get_missing_texture(f'missing_{texture_name}', default_color)

    @staticmethod
    def clamp_value(value, min_value=0.0, max_value=1.0):
        return min(max_value, max(value, min_value))

    @staticmethod
    def new_texture_name_with_suffix(old_name, suffix, ext):
        old_name = Path(old_name)
        return f'{old_name.with_name(old_name.stem)}_{suffix}.{ext}'

    def clean_nodes(self):
        for node in self.bpy_material.node_tree.nodes:
            self.bpy_material.node_tree.nodes.remove(node)

    def create_node(self, node_type: str, name: str = None):
        node = self.bpy_material.node_tree.nodes.new(node_type)
        if name:
            node.name = name
            node.label = name
        return node

    def create_node_group(self, group_name, location=None, *, name=None):
        group_node = self.create_node(Nodes.ShaderNodeGroup, name or group_name)
        group_node.node_tree = bpy.data.node_groups.get(group_name)
        group_node.width = group_node.bl_width_max
        if location is not None:
            group_node.location = location
        return group_node

    def create_texture_node(self, texture, name=None, location=None):
        texture_node = self.create_node(Nodes.ShaderNodeTexImage, name)
        if texture is not None:
            texture_node.image = texture
        if location is not None:
            texture_node.location = location
        return texture_node

    def create_and_connect_texture_node(self, texture, color_out_target=None, alpha_out_target=None, *, name=None,
                                        UV=None):
        texture_node = self.create_texture_node(texture, name)
        if color_out_target is not None:
            self.connect_nodes(texture_node.outputs['Color'], color_out_target)
        if alpha_out_target is not None:
            self.connect_nodes(texture_node.outputs['Alpha'], alpha_out_target)
        if UV is not None:
            self.connect_nodes(UV.outputs[0], texture_node.inputs[0])
        return texture_node

    def get_node(self, name):
        return self.bpy_material.node_tree.nodes.get(name, None)

    def connect_nodes(self, output_socket, input_socket):
        self.bpy_material.node_tree.links.new(output_socket, input_socket)

    def insert_node(self, output_socket, middle_input_socket, middle_output_socket):
        receivers = []
        for link in output_socket.links:
            receivers.append(link.to_socket)
            self.bpy_material.node_tree.links.remove(link)
        self.connect_nodes(output_socket, middle_input_socket)
        for receiver in receivers:
            self.connect_nodes(middle_output_socket, receiver)

    def create_nodes(self, material_name: str):
        self.logger.info(f'Creating material {repr(material_name)}')
        self.bpy_material = bpy.data.materials.get(material_name, False) or bpy.data.materials.new(material_name)

        if self.bpy_material is None:
            self.logger.error('Failed to get or create material')
            return 'UNKNOWN'

        if self.bpy_material.get('source_loaded'):
            return 'LOADED'

        self.bpy_material.use_nodes = True
        self.clean_nodes()
        self.bpy_material.blend_method = 'OPAQUE'
        self.bpy_material.shadow_method = 'OPAQUE'
        self.bpy_material.use_screen_refraction = False
        self.bpy_material.refraction_depth = 0.2
        self.bpy_material['source_loaded'] = True

    def align_nodes(self):
        if not self.do_arrange:
            return
        nodes_iterate(self.bpy_material.node_tree)
        self.bpy_material.node_tree.nodes.update()

    def handle_transform(self, transform: Tuple, socket: bpy.types.NodeSocket, loc=None, *, UV=None):
        sys.stdout.write(repr(transform))
        if (loc is None):
            loc = socket.node.location
        if UV is not None:
            uv = UV
            uv.location = [-300 + loc[0], uv.location[1]]
            if self.UVmap is not None:
                self.UVmap.location = [-500 + loc[0], self.UVmap.location[1]]
        else:
            uv = self.create_node("ShaderNodeUVMap")
            uv.location = [-300 + loc[0], -20 + loc[1]]
        mapping = self.create_node("ShaderNodeMapping")
        mapping.location = [-150 + loc[0], -20 + loc[1]]
        self.connect_nodes(uv.outputs[0], mapping.inputs[0])
        mapping.inputs[1].default_value = transform['translate']
        mapping.inputs[2].default_value = transform['rotate']
        mapping.inputs[3].default_value = transform['scale']
        # nodegroup.inputs[4].default_value = transform['center']
        self.connect_nodes(mapping.outputs[0], socket)
        return mapping, uv
