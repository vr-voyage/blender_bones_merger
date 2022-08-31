import bpy

bl_info = {
    "author": "Voyage (VRSNS)",
    "name": "Adds the ability to merge bones and Vertex Groups in one click",
    "description": "Merge selected bones with active",
    "location": "Armature Context Menu > Merge with active",
    "category": "Rigging",
    "support": "COMMUNITY",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "warning": "",
    "doc_url": "",
}

langs = {
    'ja_JP': {
        ('Operator', 'Merge with active'): 'アクティブ・ボーンと結合',
        ('*', 'Merge selected bones and their vertex groups with the active bone'): '関連頂点グループと共に、選択したボーンとアクティブボーンを結合する',
        ('*', 'Armature Context Menu > Merge with active'): 'アーマチュアコンテクストメニュー > アクティブ・ボーンと結合',
        ('*', 'Merge selected bones and associated Vertex Groups'): '選択したボーンとその頂点グループを結合する',
        ('*', 'You MUST be in "Edit Armature" mode to use this tool.'): 'このツールはアーマチュア編集モードでしか使えません。',
        ('*', 'No associated Mesh. Forgot to add the Armature modifier ? Is the armature modifier using Vertex groups ?'): 'アーマチュアと繋がるMeshがありません。アーマチュア・モディファイアを忘れましたか？バインド先：頂点グループのチェックを入れましたか？',
        ('*', 'The active bone has no vertex group associated. Create it before.'): 'アクティブボーンの同名頂点グループが存在しません。そのグループを追加してください。',
        ('*', "This tool doesn't work with Mirror X enabled.\nDisable it by clicking on the X near butterfly icon at the top right of the 3D view."): "X軸ミラーの状態で使えません。3Dビューの右上の蝶々アイコンで、X軸ミラーを無効してください。",
        ('*', "No vertex groups named like the Active Bone were found. Create it before using this operator."): "すべての関連Meshで\nアクティブ・ボーンの同じ名前を持つ頂点グループが存在することを確認してください。",
        ('*', "Currently, this tool doesn't work when two or more meshes are bound to the same Armature."): "現在、アーマチュアに二個以上のMeshが付けている場合で、このツールは使うことが出来ません。"
    }
}

# Generate an operator, with almost the same code,
# and add it to the Bones selection context menu.
# This time, the operator will :
# * Merge the vertex groups of selected bones with
#   the active one
# * Delete the merged vertex groups, and the selected
#   bones beside the active one

class VoyageVRSNSBonesMergerOperator(bpy.types.Operator):
    bl_idname = "armature.voyage_vrsns_merge_bones"
    bl_label  = "Merge with active"
    bl_description = "Merge selected bones and their vertex groups with the active bone"

    @classmethod
    def poll(cls, context):
        return len(bpy.context.selected_bones) > 0

    def invoke(self, context, event):
        return self.execute(context)

    def print_error(self, message):
        self.report({'ERROR'}, bpy.app.translations.pgettext(message))

    # Function to get the mesh associated with the
    # armature.
    # Since the linking is done through Modifiers,
    # I'll check for the ArmatureModifier of each object,
    # when applicable.
    def get_associated_meshes(self, armature) -> list[bpy.types.Object]:
        associated_meshes = []
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
                if not modifier.use_vertex_groups:
                    continue
                associated_meshes.append(o)
        return associated_meshes

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

        if armature.data.use_mirror_x:
            self.print_error("This tool doesn't work with Mirror X enabled.\nDisable it by clicking on the X near butterfly icon at the top right of the 3D view.")
            return {'FINISHED'}

        # Get the associated Mesh
        meshes = self.get_associated_meshes(armature)

        # Quit if we don't know which Mesh is associated
        # with this armature
        if not meshes:
            self.print_error('No associated Mesh. Forgot to add the Armature modifier ? Is the armature modifier using Vertex groups ?')
            return {'FINISHED'}

        if len(meshes) > 1:
            self.print_error("Currently, this tool doesn't work when two or more meshes are bound to the same Armature.")
            return {'FINISHED'}

        mesh = meshes[0]

        # Get the current active bone
        active_bone = bpy.context.active_bone

        # This will have to be defined through a UI...
        target_vertex_group_name = active_bone.name

        # Preliminary check
        # Quit if the mesh have no such vertex group actually
        if target_vertex_group_name not in mesh.vertex_groups:
            self.print_error('No vertex groups named like the Active Bone were found. Create it before using this operator.')
            return {'FINISHED'}

        # Perform the operation
        # Get the targeted VertexGroup object
        target_vertex_group = mesh.vertex_groups[target_vertex_group_name]

        ## Generate the vertex groups cache
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
    self.layout.separator()
    self.layout.operator(VoyageVRSNSBonesMergerOperator.bl_idname, text="Merge with active")

def register():
    bpy.app.translations.register(__name__, langs)
    bpy.utils.register_class(VoyageVRSNSBonesMergerOperator)
    bpy.types.VIEW3D_MT_armature_context_menu.append(menu_func)
    

def unregister():
    bpy.utils.unregister_class(VoyageVRSNSBonesMergerOperator)
    bpy.types.VIEW3D_MT_armature_context_menu.remove(menu_func)
    bpy.app.translations.unregister(__name__)

if __name__ == "__main__":
    register()
