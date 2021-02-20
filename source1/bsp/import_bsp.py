import json
import math
import re
from pathlib import Path
from pprint import pprint
from typing import Optional, List, Tuple, Dict, Any

import bpy
import numpy as np

from .bsp_file import BSPFile
from .datatypes.gamelumps.static_prop_lump import StaticPropLump
from .entities.base_entity_handler import BaseEntityHandler
from .entities.tf2_entity_handler import TF2EntityHandler
from .lumps.displacement_lump import DispVert, DispInfoLump, DispMultiblend
from .lumps.edge_lump import EdgeLump
from .lumps.entity_lump import EntityLump
from .lumps.face_lump import FaceLump
from .lumps.game_lump import GameLump
from .lumps.model_lump import ModelLump
from .lumps.pak_lump import PakLump
from .lumps.string_lump import StringsLump
from .lumps.surf_edge_lump import SurfEdgeLump
from .lumps.texture_lump import TextureInfoLump, TextureDataLump
from .lumps.vertex_lump import VertexLump
from ...bpy_utilities.logging import BPYLoggingManager
from ...bpy_utilities.material_loader.material_loader import Source1MaterialLoader
from ...bpy_utilities.utils import get_material, get_or_create_collection
from ...source_shared.content_manager import ContentManager
from ...utilities.keyvalues import KVParser
from ...utilities.math_utilities import parse_hammer_vector, convert_rotation_source1_to_blender, lerp_vec, \
    clamp_value, HAMMER_UNIT_TO_METERS

strip_patch_coordinates = re.compile(r"_-?\d+_-?\d+_-?\d+.*$")
log_manager = BPYLoggingManager()


def get_entity_name(entity_data: Dict[str, Any]):
    return f'{entity_data.get("targetname", entity_data.get("hammerid", "missing_hammer_id"))}'


class BSP:
    def __init__(self, map_path, *, scale=1.0):
        self.filepath = Path(map_path)
        self.logger = log_manager.get_logger(self.filepath.name)
        self.logger.info(f'Loading map "{self.filepath}"')
        self.map_file = BSPFile(self.filepath)
        self.map_file.parse()
        self.scale = scale
        self.main_collection = bpy.data.collections.new(self.filepath.name)
        bpy.context.scene.collection.children.link(self.main_collection)
        self.entry_cache = {}
        self.model_lump: Optional[ModelLump] = self.map_file.get_lump('LUMP_MODELS')
        self.vertex_lump: Optional[VertexLump] = self.map_file.get_lump('LUMP_VERTICES')
        self.edge_lump: Optional[EdgeLump] = self.map_file.get_lump('LUMP_EDGES')
        self.surf_edge_lump: Optional[SurfEdgeLump] = self.map_file.get_lump('LUMP_SURFEDGES')
        self.face_lump: Optional[FaceLump] = self.map_file.get_lump('LUMP_FACES')
        self.texture_info_lump: Optional[TextureInfoLump] = self.map_file.get_lump('LUMP_TEXINFO')
        self.texture_data_lump: Optional[TextureDataLump] = self.map_file.get_lump('LUMP_TEXDATA')

        content_manager = ContentManager()

        provider = content_manager.get_content_provider_from_path(self.filepath)
        if provider.steam_id in [1840, 440]:
            self.entity_handler = TF2EntityHandler(self.map_file, self.main_collection, self.scale)
        else:
            self.entity_handler = BaseEntityHandler(self.map_file, self.main_collection, self.scale)

        self.logger.debug('Adding map pack file to content manager')
        content_manager.content_providers[Path(self.filepath).stem] = self.map_file.get_lump('LUMP_PAK')

    def get_string(self, string_id):
        strings_lump: Optional[StringsLump] = self.map_file.get_lump('LUMP_TEXDATA_STRING_TABLE')
        return strings_lump.strings[string_id] or "NO_NAME"

    def load_entities(self):
        entity_lump: Optional[EntityLump] = self.map_file.get_lump('LUMP_ENTITIES')
        self.entry_cache = {k['targetname']: k for k in entity_lump.entities if 'targetname' in k}
        if entity_lump:
            entities_json = bpy.data.texts.new(
                f'{self.filepath.stem}_entities.json')
            json.dump(entity_lump.entities, entities_json, indent=1)
            for entity_data in entity_lump.entities:
                if not self.entity_handler.handle_entity(entity_data):
                    pprint(entity_data)
            bpy.context.view_layer.update()
            for entity_data in entity_lump.entities:
                self.entity_handler.resolve_parents(entity_data)

    def load_static_props(self):
        gamelump: Optional[GameLump] = self.map_file.get_lump('LUMP_GAME_LUMP')
        if gamelump:
            static_prop_lump: StaticPropLump = gamelump.game_lumps.get('sprp', None)
            if static_prop_lump:
                parent_collection = get_or_create_collection('static_props', self.main_collection)
                for n, prop in enumerate(static_prop_lump.static_props):
                    model_name = static_prop_lump.model_names[prop.prop_type]
                    location = np.multiply(prop.origin, self.scale)
                    rotation = convert_rotation_source1_to_blender(prop.rotation)
                    self.create_empty(f'static_prop_{n}', location, rotation, None, parent_collection,
                                      custom_data={'parent_path': str(self.filepath.parent),
                                                   'prop_path': model_name,
                                                   'scale': self.scale,
                                                   'type': 'static_props',
                                                   'skin': str(prop.skin - 1 if prop.skin != 0 else 0),
                                                   'entity': {
                                                       'type': 'static_prop',
                                                       'origin': '{} {} {}'.format(*prop.origin),
                                                       'angles': '{} {} {}'.format(*prop.rotation),
                                                       'skin': str(prop.skin - 1 if prop.skin != 0 else 0),
                                                   }
                                                   })

    def load_materials(self):
        content_manager = ContentManager()

        texture_data_lump: Optional[TextureDataLump] = self.map_file.get_lump('LUMP_TEXDATA')
        pak_lump: Optional[PakLump] = self.map_file.get_lump('LUMP_PAK')
        if pak_lump:
            content_manager.content_providers[self.filepath.stem] = pak_lump
        for texture_data in texture_data_lump.texture_data:
            material_name = self.get_string(texture_data.name_id)
            tmp = strip_patch_coordinates.sub("", material_name)[-63:]
            if bpy.data.materials.get(tmp, False):
                if bpy.data.materials[tmp].get('source1_loaded'):
                    self.logger.debug(
                        f'Skipping loading of {strip_patch_coordinates.sub("", material_name)} as it already loaded')
                    continue
            self.logger.info(f"Loading {material_name} material")
            material_file = content_manager.find_material(material_name)

            if material_file:
                material_name = strip_patch_coordinates.sub("", material_name)
                mat = Source1MaterialLoader(material_file, material_name)
                mat.create_material()
            else:
                self.logger.error(f'Failed to find {material_name} material')

    def load_disp(self):
        disp_info_lump: Optional[DispInfoLump] = self.map_file.get_lump('LUMP_DISPINFO')
        if not disp_info_lump or not disp_info_lump.infos:
            return

        disp_multiblend: Optional[DispMultiblend] = self.map_file.get_lump('LUMP_DISP_MULTIBLEND')

        disp_verts_lump: Optional[DispVert] = self.map_file.get_lump('LUMP_DISP_VERTS')
        surf_edges = self.surf_edge_lump.surf_edges
        vertices = self.vertex_lump.vertices
        edges = self.edge_lump.edges

        disp_verts = disp_verts_lump.transformed_vertices

        parent_collection = get_or_create_collection('displacements', self.main_collection)
        info_count = len(disp_info_lump.infos)
        multiblend_offset = 0
        for n, disp_info in enumerate(disp_info_lump.infos):
            self.logger.info(f'Processing {n + 1}/{info_count} displacement face')
            final_vertex_colors = {}
            src_face = disp_info.source_face

            texture_info = src_face.tex_info
            texture_data = texture_info.tex_data
            tv1, tv2 = texture_info.texture_vectors

            first_edge = src_face.first_edge
            edge_count = src_face.edge_count

            used_surf_edges = surf_edges[first_edge:first_edge + edge_count]
            reverse = np.subtract(1, (used_surf_edges > 0).astype(np.uint8))
            used_edges = edges[np.abs(used_surf_edges)]
            tmp = np.arange(used_edges.shape[0])
            face_vertex_ids = used_edges[tmp, reverse]
            face_vertices = vertices[face_vertex_ids] * self.scale

            min_index = np.where(
                np.sum(
                    np.isclose(face_vertices,
                               disp_info.start_position * self.scale,
                               0.5e-2),
                    axis=1
                ) == 3)
            if min_index[0].shape[0] == 0:
                lowest = 999.e16
                for i, value in enumerate(np.sum(face_vertices - disp_info.start_position, axis=1)):
                    if value < lowest:
                        min_index = i
                        lowest = value
            else:
                min_index = min_index[0][0]

            left_edge = face_vertices[(1 + min_index) & 3] - face_vertices[min_index & 3]
            right_edge = face_vertices[(2 + min_index) & 3] - face_vertices[(3 + min_index) & 3]

            num_edge_vertices = (1 << disp_info.power) + 1
            subdivide_scale = 1.0 / (num_edge_vertices - 1)
            left_edge_step = left_edge * subdivide_scale
            right_edge_step = right_edge * subdivide_scale

            subdiv_vert_count = num_edge_vertices ** 2

            disp_vertices = np.zeros((subdiv_vert_count, 3), dtype=np.float32)
            disp_uv = np.zeros((subdiv_vert_count, 2), dtype=np.float32)
            disp_indices = np.arange(0, subdiv_vert_count, dtype=np.uint32) + disp_info.disp_vert_start
            for i in range(num_edge_vertices):
                left_end = left_edge_step * i
                left_end += face_vertices[min_index & 3]

                right_end = right_edge_step * i
                right_end += face_vertices[(3 + min_index) & 3]

                left_right_seg = right_end - left_end
                left_right_step = left_right_seg * subdivide_scale

                for j in range(num_edge_vertices):
                    disp_vertices[(i * num_edge_vertices + j)] = left_end + (left_right_step * j)
            disp_uv[:, 0] = (np.dot(disp_vertices, tv1[:3]) + tv1[3] * self.scale) / (
                    texture_data.view_width * self.scale)
            disp_uv[:, 1] = 1 - ((np.dot(disp_vertices, tv2[:3]) + tv2[3] * self.scale) / (
                    texture_data.view_height * self.scale))

            disp_vertices_alpha = disp_verts_lump.vertices['alpha'][disp_indices]
            final_vertex_colors['vertex_alpha'] = np.concatenate(
                (np.hstack([disp_vertices_alpha, disp_vertices_alpha, disp_vertices_alpha]),
                 np.ones((disp_vertices_alpha.shape[0], 1))), axis=1)

            if disp_multiblend and disp_info.has_multiblend:
                multiblend_layers = disp_multiblend.blends[multiblend_offset:multiblend_offset + subdiv_vert_count]
                final_vertex_colors['multiblend'] = multiblend_layers['multiblend']
                final_vertex_colors['alphablend'] = multiblend_layers['alphablend']
                miltiblend_color_layer = multiblend_layers['multiblend_colors']
                shape_ = multiblend_layers.shape[0]
                final_vertex_colors['multiblend_color0'] = np.concatenate((miltiblend_color_layer[:, 0, :],
                                                                           np.ones((shape_, 1))),
                                                                          axis=1)
                final_vertex_colors['multiblend_color1'] = np.concatenate((miltiblend_color_layer[:, 1, :],
                                                                           np.ones((shape_, 1))),
                                                                          axis=1)
                final_vertex_colors['multiblend_color2'] = np.concatenate((miltiblend_color_layer[:, 2, :],
                                                                           np.ones((shape_, 1))),
                                                                          axis=1)
                final_vertex_colors['multiblend_color3'] = np.concatenate((miltiblend_color_layer[:, 3, :],
                                                                           np.ones((shape_, 1))),
                                                                          axis=1)
                multiblend_offset += subdiv_vert_count

            face_indices = []
            for i in range(num_edge_vertices - 1):
                for j in range(num_edge_vertices - 1):
                    index = i * num_edge_vertices + j
                    if index & 1:
                        face_indices.append((index, index + 1, index + num_edge_vertices))
                        face_indices.append((index + 1, index + num_edge_vertices + 1, index + num_edge_vertices))
                    else:
                        face_indices.append((index, index + num_edge_vertices + 1, index + num_edge_vertices))
                        face_indices.append((index, index + 1, index + num_edge_vertices + 1,))

            mesh_obj = bpy.data.objects.new(f"{self.filepath.stem}_disp_{disp_info.map_face}",
                                            bpy.data.meshes.new(
                                                f"{self.filepath.stem}_disp_{disp_info.map_face}_MESH"))
            mesh_data = mesh_obj.data
            if parent_collection is not None:
                parent_collection.objects.link(mesh_obj)
            else:
                self.main_collection.objects.link(mesh_obj)
            mesh_data.from_pydata(disp_vertices + disp_verts[disp_indices] * self.scale, [], face_indices)

            uv_data = mesh_data.uv_layers.new().data
            vertex_indices = np.zeros((len(mesh_data.loops, )), dtype=np.uint32)
            mesh_data.loops.foreach_get('vertex_index', vertex_indices)
            uv_data.foreach_set('uv', disp_uv[vertex_indices].flatten())

            for name, vertex_color_layer in final_vertex_colors.items():
                vertex_colors = mesh_data.vertex_colors.get(name, False) or mesh_data.vertex_colors.new(name=name)
                vertex_colors_data = vertex_colors.data
                vertex_colors_data.foreach_set('color', vertex_color_layer[vertex_indices].flatten())

            material_name = self.get_string(texture_data.name_id)
            material_name = strip_patch_coordinates.sub("", material_name)[-63:]
            get_material(material_name, mesh_obj)

    def load_detail_props(self):
        content_manager = ContentManager()
        entity_lump: Optional[EntityLump] = self.map_file.get_lump('LUMP_ENTITIES')
        if entity_lump:
            worldspawn = entity_lump.entities[0]
            assert worldspawn['classname'] == 'worldspawn'
            vbsp_name = worldspawn['detailvbsp']
            vbsp_file = content_manager.find_file(vbsp_name)
            vbsp = KVParser('vbsp', vbsp_file.read().decode('ascii'))
            details_info = vbsp.parse()
            print(vbsp_file)

    def create_empty(self, name: str, location, rotation=None, scale=None, parent_collection=None, custom_data=None):
        if custom_data is None:
            custom_data = {}
        if scale is None:
            scale = [1.0, 1.0, 1.0]
        if rotation is None:
            rotation = [0.0, 0.0, 0.0]
        placeholder = bpy.data.objects.new(name, None)
        placeholder.location = location
        placeholder.rotation_euler = rotation

        placeholder.empty_display_size = 16
        placeholder.scale = np.multiply(scale, self.scale)
        placeholder['entity_data'] = custom_data
        if parent_collection is not None:
            parent_collection.objects.link(placeholder)
        else:
            self.main_collection.objects.link(placeholder)
