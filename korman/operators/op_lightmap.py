#    This file is part of Korman.
#
#    Korman is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Korman is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Korman.  If not, see <http://www.gnu.org/licenses/>.

import bpy
from ..helpers import GoodNeighbor

class _LightingOperator:
    @classmethod
    def poll(cls, context):
        if context.object is not None:
            return context.scene.render.engine == "PLASMA_GAME"

    def _hide_textures(self, mesh, toggle):
        for mat in mesh.materials:
            for tex in mat.texture_slots:
                if tex is not None and tex.use:
                    toggle.track(tex, "use", False)


class LightmapAutobakeOperator(_LightingOperator, bpy.types.Operator):
    bl_idname = "object.plasma_lightmap_autobake"
    bl_label = "Bake Lightmap"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        with GoodNeighbor() as toggle:
            # We need to ensure that we bake onto the "BlahObject_LIGHTMAPGEN" image
            obj = context.active_object
            data_images = bpy.data.images
            im_name = "{}_LIGHTMAPGEN".format(obj.name)
            size = obj.plasma_modifiers.lightmap.resolution

            im = data_images.get(im_name)
            if im is None:
                im = data_images.new(im_name, width=size, height=size)
            elif im.size != (size, size):
                # Force delete and recreate the image because the size is out of date
                im.user_clear()
                data_images.remove(im)
                im = data_images.new(im_name, width=size, height=size)
    
            # This just wraps Blender's internal lightmap UV whatchacallit...
            # We want to ensure that we use the UV Layer "LIGHTMAPGEN" and fetch the size from
            #     the lightmap modifier. What fun...
            mesh = context.active_object.data
            mesh.update()
    
            # Search for LIGHTMAPGEN
            for uvtex in mesh.uv_textures:
                if uvtex.name == "LIGHTMAPGEN":
                    toggle.track(mesh.uv_textures, "active", uvtex)
                    break
            else:
                # Gotta make it
                uvtex = mesh.uv_textures.new("LIGHTMAPGEN")
                toggle.track(mesh.uv_textures, "active", uvtex)
    
            # Now, enter edit mode on this mesh and unwrap.
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_IMG_PX_SIZE=size)
            bpy.ops.object.mode_set(mode="OBJECT")
    
            # Associate the image with all the new UVs
            for i in mesh.uv_textures.active.data:
                i.image = im
    
            # Bake settings
            render = context.scene.render
            toggle.track(render, "bake_type", "FULL")
            toggle.track(render, "use_bake_to_vertex_color", False)

            # If we run a full render with our textures enabled, guess what we will get in our LM?
            # Yeah, textures. Mutter mutter mutter.
            self._hide_textures(obj.data, toggle)

            # Now, we *finally* bake the lightmap...
            # FIXME: Don't bake Plasma RT lights
            bpy.ops.object.bake_image()

        # Done!
        return {"FINISHED"}


class LightmapAutobakePreviewOperator(_LightingOperator, bpy.types.Operator):
    bl_idname = "object.plasma_lightmap_preview"
    bl_label = "Preview Lightmap"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        bpy.ops.object.plasma_lightmap_autobake()

        tex = bpy.data.textures.get("LIGHTMAPGEN_PREVIEW")
        if tex is None:
            tex = bpy.data.textures.new("LIGHTMAPGEN_PREVIEW", "IMAGE")
        tex.extension = "CLIP"
        tex.image = bpy.data.images["{}_LIGHTMAPGEN".format(context.active_object.name)]

        return {"FINISHED"}


class VertexColorLightingOperator(_LightingOperator, bpy.types.Operator):
    bl_idname = "object.plasma_vertexlight_autobake"
    bl_label = "Bake Vertex Color Lighting"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        with GoodNeighbor() as toggle:
            mesh = context.active_object.data
            mesh.update()

            # Find the "autocolor" vertex color layer
            autocolor = mesh.vertex_colors.get("autocolor")
            if autocolor is None:
                mesh.vertex_colors.new("autocolor")
            toggle.track(mesh.vertex_colors, "active", autocolor)

            # Prepare to bake...
            self._hide_textures(mesh, toggle)
            # TODO: don't bake runtime lights

            # Bake settings
            render = context.scene.render
            toggle.track(render, "bake_type", "FULL")
            toggle.track(render, "use_bake_to_vertex_color", True)

            # Bake
            bpy.ops.object.bake_image()

        # And done!
        return {"FINISHED"}
