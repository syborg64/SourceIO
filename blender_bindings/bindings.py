from pathlib import Path

import bpy

from bpy.props import (StringProperty,
                       BoolProperty,
                       CollectionProperty,
                       IntProperty,
                       FloatProperty,
                       PointerProperty
                       )

from ..library.source1.vtf import is_vtflib_supported

from .operators.goldsrc_operators import (SOURCEIO_OT_GBSPImport,
                                          SOURCEIO_OT_GMDLImport)

from .operators.source1_operators import (SOURCEIO_OT_BSPImport,
                                          SOURCEIO_OT_MDLImport,
                                          SOURCEIO_OT_DMXImporter,
                                          SOURCEIO_OT_RigImport,
                                          )
from .operators.source2_operators import (SOURCEIO_OT_VMATImport,
                                          SOURCEIO_OT_VTEXImport,
                                          SOURCEIO_OT_VMDLImport,
                                          SOURCEIO_OT_VWRLDImport,
                                          SOURCEIO_OT_VPK_VWRLDImport,
                                          SOURCEIO_OT_DMXCameraImport
                                          )
from .operators.shared_operators import (SOURCEIO_PT_Utils,
                                         SOURCEIO_PT_Placeholders,
                                         SOURCEIO_PT_SkinChanger,
                                         SOURCEIO_OT_ChangeSkin,
                                         ChangeSkin_OT_LoadEntity,
                                         SOURCEIO_PT_Scene,
                                         )
from .operators.vpk_operators import (SourceIO_OP_VPKBrowser,
                                      SourceIO_OP_VPKBrowserLoader,
                                      )
from .operators.vpk_operators import classes as vpk_classes

from .operators.flex_operators import classes as flex_classes, SourceIO_PG_FlexController

from .ui.export_nodes import register_nodes, unregister_nodes

custom_icons = {}

# noinspection PyPep8Naming
from ..library.utils.singleton import SingletonMeta


class SourceIO_MT_Menu(bpy.types.Menu):
    bl_label = "Source Engine Assets"
    bl_idname = "IMPORT_MT_sourceio"

    def draw(self, context):
        crowbar_icon = custom_icons["main"]["crowbar_icon"]
        bsp_icon = custom_icons["main"]["bsp_icon"]
        vtf_icon = custom_icons["main"]["vtf_icon"]
        vmt_icon = custom_icons["main"]["vmt_icon"]
        model_doc_icon = custom_icons["main"]["model_doc_icon"]
        vmat_icon = custom_icons["main"]["vmat_icon"]
        vtex_icon = custom_icons["main"]["vtex_icon"]
        vwrld_icon = custom_icons["main"]["vwrld_icon"]
        layout = self.layout
        layout.operator(SOURCEIO_OT_MDLImport.bl_idname, text="Source model (.mdl)",
                        icon_value=crowbar_icon.icon_id)
        layout.operator(SOURCEIO_OT_BSPImport.bl_idname, text="Source map (.bsp)",
                        icon_value=bsp_icon.icon_id)
        if is_vtflib_supported():
            layout.operator(SOURCEIO_OT_VTFImport.bl_idname, text="Source texture (.vtf)",
                            icon_value=vtf_icon.icon_id)
            layout.operator(SOURCEIO_OT_SkyboxImport.bl_idname, text="Source Skybox (.vmt)",
                            icon_value=vtf_icon.icon_id)
            layout.operator(SOURCEIO_OT_VMTImport.bl_idname, text="Source material (.vmt)",
                            icon_value=vmt_icon.icon_id)
        layout.operator(SOURCEIO_OT_DMXImporter.bl_idname, text="[!!!WIP!!!] SFM session (.dmx) [!!!WIP!!!]")
        layout.operator(SOURCEIO_OT_RigImport.bl_idname, text="SFM ik-rig script (.py)")
        layout.separator()
        layout.operator(SOURCEIO_OT_VMDLImport.bl_idname, text="Source2 model (.vmdl)",
                        icon_value=model_doc_icon.icon_id)
        layout.operator(SOURCEIO_OT_VWRLDImport.bl_idname, text="Source2 map (.vwrld)",
                        icon_value=vwrld_icon.icon_id)
        layout.operator(SOURCEIO_OT_VPK_VWRLDImport.bl_idname, text="Source2 packed map (.vpk)",
                        icon_value=vwrld_icon.icon_id)
        layout.operator(SOURCEIO_OT_VTEXImport.bl_idname, text="Source2 texture (.vtex)",
                        icon_value=vtex_icon.icon_id)
        layout.operator(SOURCEIO_OT_VMATImport.bl_idname, text="Source2 material (.vmat)",
                        icon_value=vmat_icon.icon_id)
        layout.separator()
        layout.operator(SOURCEIO_OT_GMDLImport.bl_idname, text="GoldSrc model (.mdl)",
                        icon_value=crowbar_icon.icon_id)
        layout.operator(SOURCEIO_OT_GBSPImport.bl_idname, text="GoldSrc map (.bsp)",
                        icon_value=bsp_icon.icon_id)
        layout.separator()
        layout.operator(SourceIO_OP_VPKBrowserLoader.bl_idname, text="[!!!WIP!!!]Browse new VPK (.vpk)",
                        icon_value=bsp_icon.icon_id)
        layout.operator(SourceIO_OP_VPKBrowser.bl_idname, text="[!!!WIP!!!]Browse already open VPK (.vpk)",
                        icon_value=bsp_icon.icon_id)
        layout.separator()
        layout.menu(SourceIOUtils_MT_Menu.bl_idname)


class SourceIOUtils_MT_Menu(bpy.types.Menu):
    bl_label = "Source Engine Utils"
    bl_idname = "IMPORT_MT_sourceio_utils"

    def draw(self, context):
        layout = self.layout
        layout.operator(SOURCEIO_OT_DMXCameraImport.bl_idname, text="Valve camera(.dmx)")


def menu_import(self, context):
    source_io_icon = custom_icons["main"]["sourceio_icon"]
    self.layout.menu(SourceIO_MT_Menu.bl_idname, icon_value=source_io_icon.icon_id)


def load_icon(loader, filename, name):
    script_path = Path(__file__).parent
    icon_path = script_path / 'icons' / filename
    loader.load(name, str(icon_path), 'IMAGE')


def register_custom_icon():
    import bpy.utils.previews
    pcoll = bpy.utils.previews.new()
    load_icon(pcoll, 'sourceio_icon.png', "sourceio_icon")
    load_icon(pcoll, 'crowbar_icon.png', "crowbar_icon")
    load_icon(pcoll, 'bsp_icon.png', "bsp_icon")
    load_icon(pcoll, 'vtf_icon.png', "vtf_icon")
    load_icon(pcoll, 'vmt_icon.png', "vmt_icon")
    load_icon(pcoll, 'model_doc_icon.png', "model_doc_icon")
    load_icon(pcoll, 'vmat_icon.png', "vmat_icon")
    load_icon(pcoll, 'vtex_icon.png', "vtex_icon")
    load_icon(pcoll, 'vwrld_icon.png', "vwrld_icon")
    custom_icons["main"] = pcoll


def unregister_custom_icon():
    import bpy.utils.previews
    for pcoll in custom_icons.values():
        bpy.utils.previews.remove(pcoll)
    custom_icons.clear()


classes = (
    # GoldSrc
    SOURCEIO_OT_GBSPImport,
    SOURCEIO_OT_GMDLImport,
    # Source1 stuff

    SOURCEIO_OT_MDLImport,
    SOURCEIO_OT_BSPImport,
    SOURCEIO_OT_DMXImporter,
    SOURCEIO_OT_RigImport,

    # Source2 stuff
    SOURCEIO_OT_DMXCameraImport,
    SOURCEIO_OT_VMDLImport,
    SOURCEIO_OT_VTEXImport,
    SOURCEIO_OT_VMATImport,
    SOURCEIO_OT_VPK_VWRLDImport,
    SOURCEIO_OT_VWRLDImport,

    # Addon tools
    # SourceIOPreferences,
    SourceIO_MT_Menu,
    SourceIOUtils_MT_Menu,
    SOURCEIO_PT_Utils,
    SOURCEIO_PT_Placeholders,
    SOURCEIO_PT_SkinChanger,
    ChangeSkin_OT_LoadEntity,
    SOURCEIO_OT_ChangeSkin,
    SOURCEIO_PT_Scene,

    *vpk_classes,
    *flex_classes,
)

if is_vtflib_supported():
    from .operators.source1_operators import (SOURCEIO_OT_VTFExport,
                                              SOURCEIO_OT_VTFImport,
                                              SOURCEIO_OT_VMTImport,
                                              SOURCEIO_OT_SkyboxImport,
                                              )

    classes = tuple([*classes, SOURCEIO_OT_VTFExport, SOURCEIO_OT_VTFImport,
                     SOURCEIO_OT_VMTImport, SOURCEIO_OT_SkyboxImport])

register_, unregister_ = bpy.utils.register_classes_factory(classes)


def register():
    register_custom_icon()
    register_()
    register_nodes()
    bpy.types.TOPBAR_MT_file_import.append(menu_import)

    bpy.types.Mesh.flex_controllers = CollectionProperty(type=SourceIO_PG_FlexController)
    bpy.types.Mesh.flex_selected_index = IntProperty(default=0)

    if is_vtflib_supported():
        from ..library.source1.vtf import VTFLib
        from .operators.source1_operators import export
        bpy.types.IMAGE_MT_image.append(export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)

    if is_vtflib_supported():
        from .operators.source1_operators import export
        bpy.types.IMAGE_MT_image.remove(export)
    unregister_nodes()
    SingletonMeta.cleanup()

    unregister_custom_icon()
    unregister_()
