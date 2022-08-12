bl_info = {
    "author": "Voyage (VRSNS)",
    "name": "Merge bones with Vertex Groups",
    "description": "Merge selected bones with active",
    "location": "View3D > Armature > Merge bones with active",
    "category": "Rigging",
    "support": "TESTING",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "warning": "",
    "doc_url": "",
}

import bpy

# Generate an operator, with almost the same code,
# and add it to the Bones selection context menu.
# This time, the operator will :
# * Merge the vertex groups of selected bones with
#   the active one
# * Delete the merged vertex groups, and the selected
#   bones beside the active one

class MyyBonesMergerOperator(bpy.types.Operator):
    bl_idname = "armature.myy_merge_bones"
    bl_label  = "Merge with Active"

    @classmethod
    def poll(cls, context):
        return len(bpy.context.selected_bones) > 0

    def invoke(self, context, event):
        return self.execute(context)

    def print_error(self, message):
        print(message)

    # Function to get the mesh associated with the
    # armature.
    # Since the linking is done through Modifiers,
    # I'll check for the ArmatureModifier of each object,
    # when applicable.
    def get_associated_mesh(self, armature) -> bpy.types.Object:
        for o in bpy.context.selectable_objects:
            if o.type != 'MESH':
                continue
            if len(o.modifiers) == 0:
                continue
            for modifier in o.modifiers:
                if type(modifier) is not bpy.types.ArmatureModifier:
                    continue
                if modifier.object != armature:
                    continue
                return o
        return None

    def execute(self, context):
        ## Preparations

        # Check if we're in 'Edit armature' mode.
        # Else, I have no idea about how to get the selected
        # bones, and their associated armature
        if bpy.context.mode != 'EDIT_ARMATURE':
            self.print_error('You MUST be in "Edit Armature" mode to use this tool.')
            return {'FINISHED'}

        # Get the selected armature
        armature = bpy.context.active_object

        # Get the associated Mesh
        mesh = self.get_associated_mesh(armature)

        # Quit if we don't know which Mesh is associated
        # with this armature
        if mesh == None:
            self.print_error('No associated Mesh. Forgot to add the Armature modifier ?')
            return {'FINISHED'}

        # Get the current active bone
        active_bone = bpy.context.active_bone

        # This will have to be defined through a UI...
        target_vertex_group_name = active_bone.name

        # Quit if the mesh have no such vertex group actually
        if target_vertex_group_name not in mesh.vertex_groups:
            self.print_error('The active bone has no vertex group associated. Create it before.')
            return {'FINISHED'}

        # Get the targeted VertexGroup object
        target_vertex_group = mesh.vertex_groups[target_vertex_group_name]

        ## Generate the vertex groups
        # We'll manage the cache with a fixed size array
        cached_groups = [set() for _ in range(len(mesh.vertex_groups))]

        for v in mesh.data.vertices:
            for group_info in v.groups:
                group_index = group_info.group
                cached_groups[group_index].add((v.index, group_info.weight))

        ## Add the selected bones vertex groups weights to the target vertex group
        selected_bones = bpy.context.selected_bones

        vertex_groups_to_remove = set()

        for selected_bone in selected_bones:
            if selected_bone == active_bone:
                continue

            # Some bones have no associated vertex group.
            # Skip it if that's the case
            if selected_bone.name not in mesh.vertex_groups:
                continue

            # For each cached vertex data, add it to the target VertexGroup
            vertex_group = mesh.vertex_groups[selected_bone.name]
            for vertex_data in cached_groups[vertex_group.index]:
                target_vertex_group.add([vertex_data[0]], vertex_data[1], 'ADD')
                vertex_groups_to_remove.add(vertex_group)

        for vertex_group in vertex_groups_to_remove:
            mesh.vertex_groups.remove(vertex_group)

        active_bone.select = False
        bpy.ops.armature.delete()
        
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(MyyBonesMergerOperator.bl_idname, text="Merge with active")

def register():
    bpy.utils.register_class(MyyBonesMergerOperator)
    bpy.types.VIEW3D_MT_armature_context_menu.append(menu_func)


def unregister():
    bpy.utils.unregister_class(MyyBonesMergerOperator)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)

if __name__ == "__main__":
    register()
