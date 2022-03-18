from pathlib import Path
from typing import BinaryIO, Optional

import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler

from ....library.goldsrc.mdl_v10.mdl_file import Mdl
from ....library.goldsrc.mdl_v10.structs.texture import StudioTexture
from ...material_loader.shaders.goldsrc_shaders.goldsrc_shader import GoldSrcShader
from ...utils.utils import get_new_unique_collection, get_material
from ...shared.model_container import GoldSrcModelContainer


def create_armature(mdl: Mdl, collection, scale):
    model_name = Path(mdl.header.name).stem
    armature = bpy.data.armatures.new(f"{model_name}_ARM_DATA")
    armature_obj = bpy.data.objects.new(f"{model_name}_ARM", armature)
    armature_obj['MODE'] = 'SourceIO'
    armature_obj.show_in_front = True
    collection.objects.link(armature_obj)

    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')

    for n, mdl_bone_info in enumerate(mdl.bones):
        if not mdl_bone_info.name:
            mdl_bone_info.name = f'Bone_{n}'
        mdl_bone = armature.edit_bones.new(mdl_bone_info.name)
        mdl_bone.head = Vector(mdl_bone_info.pos) * scale
        mdl_bone.tail = (Vector([0, 0, 0.25]) * scale) + mdl_bone.head
        if mdl_bone_info.parent != -1:
            mdl_bone.parent = armature.edit_bones.get(mdl.bones[mdl_bone_info.parent].name)

    bpy.ops.object.mode_set(mode='POSE')

    mdl_bone_transforms = []

    for mdl_bone_info in mdl.bones:
        mdl_bone = armature_obj.pose.bones.get(mdl_bone_info.name)
        mdl_bone_pos = Vector(mdl_bone_info.pos) * scale
        mdl_bone_rot = Euler(mdl_bone_info.rot).to_matrix().to_4x4()
        mdl_bone_mat = Matrix.Translation(mdl_bone_pos) @ mdl_bone_rot
        mdl_bone.matrix.identity()
        mdl_bone.matrix = mdl_bone.parent.matrix @ mdl_bone_mat if mdl_bone.parent else mdl_bone_mat

        if mdl_bone.parent:
            mdl_bone_transforms.append(mdl_bone_transforms[mdl_bone_info.parent] @ mdl_bone_mat)
        else:
            mdl_bone_transforms.append(mdl_bone_mat)

    bpy.ops.pose.armature_apply()
    bpy.ops.object.mode_set(mode='OBJECT')
    return armature_obj, mdl_bone_transforms


def import_model(mdl_file: BinaryIO, mdl_texture_file: Optional[BinaryIO], scale=1.0,
                 parent_collection=None, disable_collection_sort=False, re_use_meshes=False):
    if parent_collection is None:
        parent_collection = bpy.context.scene.collection

    mdl = Mdl(mdl_file)
    mdl.read()
    mdl_file_textures = mdl.textures
    if not mdl_file_textures and mdl_texture_file is not None:
        mdl_filet = Mdl(mdl_texture_file)
        mdl_filet.read()
        mdl_file_textures = mdl_filet.textures

    model_container = GoldSrcModelContainer(mdl)

    model_name = Path(mdl.header.name).stem + '_MODEL'
    master_collection = get_new_unique_collection(model_name, parent_collection)

    armature, bone_transforms = create_armature(mdl, master_collection, scale)
    model_container.armature = armature

    for body_part in mdl.bodyparts:
        mdl_body_part_collection = get_new_unique_collection(
            body_part.name, master_collection) if not disable_collection_sort else master_collection

        for body_part_model in body_part.models:
            model_name = body_part_model.name
            used_copy = False
            model_object = None

            if re_use_meshes:
                mesh_obj_original = bpy.data.objects.get(model_name, None)
                mesh_data_original = bpy.data.meshes.get(f'{model_name}_mesh', False)
                if mesh_obj_original and mesh_data_original:
                    model_mesh = mesh_data_original.copy()
                    model_object = mesh_obj_original.copy()
                    # mesh_obj['skin_groups'] = mesh_obj_original['skin_groups']
                    # mesh_obj['active_skin'] = mesh_obj_original['active_skin']
                    model_object['model_type'] = 'goldsc'
                    model_object.data = model_mesh
                    used_copy = True

            if not re_use_meshes or not used_copy:
                model_mesh = bpy.data.meshes.new(f'{model_name}_mesh')
                model_object = bpy.data.objects.new(f'{model_name}', model_mesh)

            if body_part_model.vertex_count==0:
                continue

            mdl_body_part_collection.objects.link(model_object)
            model_container.objects.append(model_object)
            model_container.bodygroups[body_part.name].append(model_object)

            modifier = model_object.modifiers.new(name='Skeleton', type='ARMATURE')
            modifier.object = armature
            model_object.parent = armature

            if used_copy:
                continue
            model_vertices = body_part_model.vertices * scale
            model_indices = []
            model_materials = []

            uv_per_mesh = []

            for model_index, body_part_model_mesh in enumerate(body_part_model.meshes):
                mesh_texture = mdl_file_textures[body_part_model_mesh.skin_ref]
                model_materials.extend(np.full(body_part_model_mesh.triangle_count, body_part_model_mesh.skin_ref))

                for mesh_triverts, mesh_triverts_fan in body_part_model_mesh.triangles:
                    if mesh_triverts_fan:
                        for index in range(1, len(mesh_triverts) - 1):
                            v0 = mesh_triverts[0]
                            v1 = mesh_triverts[index + 1]
                            v2 = mesh_triverts[index]

                            model_indices.append([v0.vertex_index, v1.vertex_index, v2.vertex_index])
                            uv_per_mesh.append({
                                v0.vertex_index: (v0.uv[0] / mesh_texture.width, 1 - v0.uv[1] / mesh_texture.height),
                                v1.vertex_index: (v1.uv[0] / mesh_texture.width, 1 - v1.uv[1] / mesh_texture.height),
                                v2.vertex_index: (v2.uv[0] / mesh_texture.width, 1 - v2.uv[1] / mesh_texture.height)
                            })
                    else:
                        for index in range(len(mesh_triverts) - 2):
                            v0 = mesh_triverts[index]
                            v1 = mesh_triverts[index + 2 - (index & 1)]
                            v2 = mesh_triverts[index + 1 + (index & 1)]

                            model_indices.append([v0.vertex_index, v1.vertex_index, v2.vertex_index])
                            uv_per_mesh.append({
                                v0.vertex_index: (v0.uv[0] / mesh_texture.width, 1 - v0.uv[1] / mesh_texture.height),
                                v1.vertex_index: (v1.uv[0] / mesh_texture.width, 1 - v1.uv[1] / mesh_texture.height),
                                v2.vertex_index: (v2.uv[0] / mesh_texture.width, 1 - v2.uv[1] / mesh_texture.height)
                            })
            remap = {}
            for model_material_index in np.unique(model_materials):
                model_texture_info = mdl_file_textures[model_material_index]
                remap[model_material_index] = load_material(model_texture_info, model_object)

            model_mesh.from_pydata(model_vertices, [], model_indices)
            model_mesh.update()
            model_mesh.polygons.foreach_set('material_index', [remap[a] for a in model_materials])

            model_mesh.uv_layers.new()
            model_mesh_uv = model_mesh.uv_layers[0].data
            for poly in model_mesh.polygons:
                for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                    model_mesh_uv[loop_index].uv = uv_per_mesh[poly.index][model_mesh.loops[loop_index].vertex_index]

            mdl_vertex_groups = {}
            for vertex_index, vertex_info in enumerate(body_part_model.bone_vertex_info):
                mdl_vertex_group = mdl_vertex_groups.setdefault(vertex_info, [])
                mdl_vertex_group.append(vertex_index)

            for vertex_bone_index, vertex_bone_vertices in mdl_vertex_groups.items():
                vertex_group_bone = mdl.bones[vertex_bone_index]
                vertex_group = model_object.vertex_groups.new(name=vertex_group_bone.name)
                vertex_group.add(vertex_bone_vertices, 1.0, 'ADD')
                vertex_group_transform = bone_transforms[vertex_bone_index]
                for vertex in vertex_bone_vertices:
                    model_mesh.vertices[vertex].co = vertex_group_transform @ model_mesh.vertices[vertex].co

    return model_container


def load_material(model_texture_info: StudioTexture, model_object):
    mat_id = get_material(model_texture_info.name, model_object)
    bpy_material = GoldSrcShader(model_texture_info)
    bpy_material.create_nodes(model_texture_info.name)
    bpy_material.align_nodes()
    return mat_id
