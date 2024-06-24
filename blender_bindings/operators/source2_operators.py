from pathlib import Path

import bpy
from bpy.props import (BoolProperty, CollectionProperty, FloatProperty,
                       IntProperty, StringProperty)

from .operator_helper import ImportOperatorHelper
from ..source2.vphy_loader import load_physics
from ..utils.resource_utils import serialize_mounted_content, deserialize_mounted_content
from ...library.shared.content_providers.content_manager import ContentManager
from ...library.shared.content_providers.vpk_provider import VPKContentProvider
from ...library.source2 import (CompiledMaterialResource,
                                CompiledModelResource, CompiledTextureResource, CompiledPhysicsResource)
from ...library.source2.resource_types.compiled_world_resource import \
    CompiledMapResource
from ...library.utils import FileBuffer
from ...library.utils.math_utilities import SOURCE2_HAMMER_UNIT_TO_METERS
from ..source2.dmx.camera_loader import load_camera
from ..source2.vmat_loader import load_material
from ..source2.vmdl_loader import load_model, put_into_collections
from ..source2.vtex_loader import import_texture
from ..source2.vwrld.loader import load_map
from ..utils.bpy_utils import get_new_unique_collection, is_blender_4_1


# noinspection PyPep8Naming
class SOURCEIO_OT_VMDLImport(ImportOperatorHelper):
    """Load Source2 VMDL"""
    bl_idname = "sourceio.vmdl"
    bl_label = "Import Source2 VMDL file"
    bl_options = {'UNDO'}

    discover_resources: BoolProperty(name="Mount discovered content", default=True)
    # invert_uv: BoolProperty(name="Invert UV", default=True)
    import_physics: BoolProperty(name="Import physics", default=False)
    import_materials: BoolProperty(name="Import materials", default=True)
    import_attachments: BoolProperty(name="Import attachments", default=False)
    lod_mask: IntProperty(name="Lod mask", default=0xFFFF, subtype="UNSIGNED")
    scale: FloatProperty(name="World scale", default=SOURCE2_HAMMER_UNIT_TO_METERS, precision=6)

    filter_glob: StringProperty(default="*.vmdl_c", options={'HIDDEN'})

    def execute(self, context):
        directory = self.get_directory()
        content_manager = ContentManager()
        if self.discover_resources:
            content_manager.scan_for_content(directory)
            serialize_mounted_content(content_manager)
        else:
            deserialize_mounted_content(content_manager)

        for n, file in enumerate(self.files):
            print(f"Loading {n + 1}/{len(self.files)}")
            with FileBuffer(directory / file.name) as f:
                model_resource = CompiledModelResource.from_buffer(f, directory / file.name)
                container = load_model(model_resource, self.scale, self.lod_mask,
                                       self.import_physics, self.import_attachments,
                                       self.import_materials)

            master_collection = get_new_unique_collection(model_resource.name, bpy.context.scene.collection)
            put_into_collections(container, Path(model_resource.name).stem, master_collection, False)

        return {'FINISHED'}


# noinspection PyPep8Naming
class SOURCEIO_OT_VMAPImport(ImportOperatorHelper):
    """Load Source2 VWRLD"""
    bl_idname = "sourceio.vmap"
    bl_label = "Import Source2 VMAP file"
    bl_options = {'UNDO'}

    filter_glob: StringProperty(default="*.vmap_c", options={'HIDDEN'})
    discover_resources: BoolProperty(name="Mount discovered content", default=True)
    # invert_uv: BoolProperty(name="invert UV?", default=True)
    import_physics: BoolProperty(name="Import physics", default=False)
    scale: FloatProperty(name="World scale", default=SOURCE2_HAMMER_UNIT_TO_METERS, precision=6)

    def execute(self, context):
        directory = self.get_directory()
        for n, file in enumerate(self.files):
            print(f"Loading {n}/{len(self.files)}")
            cm = ContentManager()
            content_manager = ContentManager()
            if self.discover_resources:
                cm.scan_for_content(directory.parent)
                serialize_mounted_content(content_manager)
            else:
                deserialize_mounted_content(content_manager)
            file_stem = Path(file.name).stem
            cm.register_content_provider(file_stem + ".vpk",
                                         VPKContentProvider(directory / f"{file_stem}.vpk"))
            with FileBuffer(directory / file.name) as buffer:
                model = CompiledMapResource.from_buffer(buffer, Path(file.name))
                load_map(model, ContentManager(), self.scale)

            if self.import_physics:
                map_collection = bpy.data.collections[file_stem]

                phys_file = ContentManager().find_file(f"maps/{file_stem}/world_physics.vphys_c")
                phys_res = CompiledPhysicsResource.from_buffer(phys_file, Path(f"maps/{file_stem}/world_physics.vphys_c"))
                phys_collection = bpy.data.collections.new("physics")
                map_collection.children.link(phys_collection)
                objects = load_physics(phys_res.get_data_block(block_name="DATA")[0])
                for obj in objects:
                    phys_collection.objects.link(obj)

            serialize_mounted_content(cm)
        return {'FINISHED'}


# noinspection PyPep8Naming
class SOURCEIO_OT_VPK_VMAPImport(ImportOperatorHelper):
    """Load Source2 VWRLD"""
    bl_idname = "sourceio.vmap_vpk"
    bl_label = "Import Source2 VMAP file from VPK"
    bl_options = {'UNDO'}

    filter_glob: StringProperty(default="*.vpk", options={'HIDDEN'})
    discover_resources: BoolProperty(name="Mount discovered content", default=True)
    # invert_uv: BoolProperty(name="invert UV?", default=True)
    import_physics: BoolProperty(name="Import physics", default=False)
    scale: FloatProperty(name="World scale", default=SOURCE2_HAMMER_UNIT_TO_METERS, precision=6)

    def execute(self, context):
        vpk_path = Path(self.filepath)
        assert vpk_path.is_file(), 'Not a file'
        cm = ContentManager()
        content_manager = ContentManager()
        if self.discover_resources:
            cm.scan_for_content(vpk_path.parent)
            serialize_mounted_content(content_manager)
        else:
            deserialize_mounted_content(content_manager)
        cm.register_content_provider(vpk_path.name, VPKContentProvider(vpk_path))

        map_buffer = ContentManager().find_file(f'maps/{vpk_path.stem}.vmap_c')
        assert map_buffer is not None, "Failed to find world file in selected VPK"

        model = CompiledMapResource.from_buffer(map_buffer, vpk_path)
        load_map(model, ContentManager(), self.scale)
        if self.import_physics:
            map_collection = bpy.data.collections[vpk_path.stem]

            phys_file = ContentManager().find_file(f"maps/{vpk_path.stem}/world_physics.vphys_c")
            phys_res = CompiledPhysicsResource.from_buffer(phys_file, Path(f"maps/{vpk_path.stem}/world_physics.vphys_c"))
            phys_collection = bpy.data.collections.new("physics")
            map_collection.children.link(phys_collection)
            objects = load_physics(phys_res.get_data_block(block_name="DATA")[0])
            for obj in objects:
                phys_collection.objects.link(obj)

        serialize_mounted_content(cm)

        return {'FINISHED'}


# noinspection PyPep8Naming
class SOURCEIO_OT_VMATImport(ImportOperatorHelper):
    """Load Source2 material"""
    bl_idname = "sourceio.vmat"
    bl_label = "Import Source2 VMDL file"
    bl_options = {'UNDO'}

    discover_resources: BoolProperty(name="Mount discovered content", default=True)
    flip: BoolProperty(name="Flip texture", default=True)
    split_alpha: BoolProperty(name="Extract alpha texture", default=True)
    filter_glob: StringProperty(default="*.vmat_c", options={'HIDDEN'})

    def execute(self, context):
        directory = self.get_directory()
        content_manager = ContentManager()
        if self.discover_resources:
            content_manager.scan_for_content(directory)
            serialize_mounted_content(content_manager)
        else:
            deserialize_mounted_content(content_manager)
        for n, file in enumerate(self.files):
            print(f"Loading {n + 1}/{len(self.files)}")
            with FileBuffer(directory / file.name) as f:
                material_resource = CompiledMaterialResource.from_buffer(f, directory / file.name)
                load_material(material_resource, Path(file.name))
        return {'FINISHED'}


# noinspection PyPep8Naming
class SOURCEIO_OT_VTEXImport(ImportOperatorHelper):
    """Load Source Engine VTF texture"""
    bl_idname = "sourceio.vtex"
    bl_label = "Import VTEX"
    bl_options = {'UNDO'}
    need_popup = False

    filter_glob: StringProperty(default="*.vtex_c", options={'HIDDEN'})

    def execute(self, context):
        directory = self.get_directory()
        for file in self.files:
            with FileBuffer(directory / file.name) as f:
                texture_resource = CompiledTextureResource.from_buffer(f, directory / file.name)
                image = import_texture(texture_resource, Path(file.name))

                if is_blender_4_1():
                    if (context.region and context.region.type == 'WINDOW'
                            and context.area and context.area.ui_type == 'ShaderNodeTree'
                            and context.object and context.object.type == 'MESH'
                            and context.material):
                        node_tree = context.material.node_tree
                        image_node = node_tree.nodes.new(type="ShaderNodeTexImage")
                        image_node.image = image
                        image_node.location = context.space_data.cursor_location
                        for node in context.material.node_tree.nodes:
                            node.select = False
                        image_node.select = True
                    if (context.region and context.region.type == 'WINDOW'
                            and context.area and context.area.ui_type in ["IMAGE_EDITOR", "UV"]):
                        context.space_data.image = image
        return {'FINISHED'}

class SOURCEIO_OT_VPHYSImport(ImportOperatorHelper):
    bl_idname = "sourceio.vphys"
    bl_label = "Import VPHYS"
    bl_options = {'UNDO'}
    need_popup = True

    filter_glob: StringProperty(default="*.vphys_c", options={'HIDDEN'})
    discover_resources: BoolProperty(name="Mount discovered content", default=True)
    scale: FloatProperty(name="World scale", default=SOURCE2_HAMMER_UNIT_TO_METERS, precision=6)

    def execute(self, context):
        directory = self.get_directory()
        content_manager = ContentManager()
        if self.discover_resources:
            content_manager.scan_for_content(directory)
            serialize_mounted_content(content_manager)
        else:
            deserialize_mounted_content(content_manager)

        for n, file in enumerate(self.files):
            print(f"Loading {n + 1}/{len(self.files)}")
            with FileBuffer(directory / file.name) as f:
                model_resource = CompiledPhysicsResource.from_buffer(f, directory / file.name)
                container = load_physics(model_resource, self.scale)

            master_collection = get_new_unique_collection(model_resource.name, bpy.context.scene.collection)
            put_into_collections(container, Path(model_resource.name).stem, master_collection, False)

        return {'FINISHED'}

# noinspection PyPep8Naming
class SOURCEIO_OT_DMXCameraImport(ImportOperatorHelper):
    """Load Valve DMX camera data"""
    bl_idname = "sourceio.dmx_camera"
    bl_label = "Import DMX camera"
    bl_options = {'UNDO'}

    filter_glob: StringProperty(default="*.dmx", options={'HIDDEN'})

    def execute(self, context):
        directory = self.get_directory()
        for file in self.files:
            load_camera(directory / file.name)
        return {'FINISHED'}
