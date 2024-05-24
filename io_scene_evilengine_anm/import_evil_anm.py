import bpy
from mathutils import Matrix
from os import path
from .anm import Anim_V1, Anim_V2, InvalidAnimation


def invalid_file_format(self, context):
    self.layout.label(text='Invalid anim file!')


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to import animation')


def bones_number_mismatch(self, context):
    self.layout.label(text='Bones number mismatch')


def set_keyframe(curves, frame, values):
    for i, c in enumerate(curves):
        c.keyframe_points.add(1)
        c.keyframe_points[-1].co = frame, values[i]
        c.keyframe_points[-1].interpolation = 'LINEAR'


def create_action(arm_obj, anm, fps, version):
    act = bpy.data.actions.new('action')
    curves_loc, curves_rot = [], []
    loc_mats, prev_rots = {}, {}

    for pose_bone in arm_obj.pose.bones:
        act.groups.new(pose_bone.name)
        pose_bone.rotation_mode = 'QUATERNION'

        curves_loc.append([
            act.fcurves.new(
                data_path=f'pose.bones["{pose_bone.name}"].location',
                index=loc,
                action_group=f"{pose_bone.name}"
            ) for loc in range(3)
        ])

        curves_rot.append([
            act.fcurves.new(
                data_path=f'pose.bones["{pose_bone.name}"].rotation_quaternion',
                index=rot,
                action_group=f"{pose_bone.name}"
            ) for rot in range(4)
        ])

        pose_bone.location = (0, 0, 0)
        pose_bone.rotation_quaternion = (1, 0, 0, 0)

        bone = arm_obj.data.bones.get(pose_bone.name)
        loc_mat = bone.matrix_local.copy()
        if bone.parent:
            loc_mat = bone.parent.matrix_local.inverted_safe() @ loc_mat
        loc_mats[pose_bone] = loc_mat
        prev_rots[pose_bone] = None

    set_kfs = []

    arm_bones_num, anm_bones_num = len(arm_obj.pose.bones), len(anm.offsets[0])
    if arm_bones_num > anm_bones_num:
        arm_bones_num = anm_bones_num

    for off_index in range(len(anm.offsets)+1):
        if off_index != len(anm.offsets):
            off = anm.offsets[off_index]
        for bone_id, pose_bone in enumerate(arm_obj.pose.bones[:arm_bones_num]):
            kf_id = off[bone_id] if off_index != len(anm.offsets) else off[bone_id]+1

            if kf_id in set_kfs:
                continue
            set_kfs.append(kf_id)

            kf = anm.keyframes[kf_id]

            loc_mat = loc_mats[pose_bone]
            loc_pos = loc_mat.to_translation()
            loc_rot = loc_mat.to_quaternion()

            rot = loc_rot.rotation_difference(kf.rot)

            prev_rot = prev_rots[pose_bone]
            if prev_rot:
                alt_rot = rot.copy()
                alt_rot.negate()
                if rot.rotation_difference(prev_rot).angle > alt_rot.rotation_difference(prev_rot).angle:
                    rot = alt_rot
            prev_rots[pose_bone] = rot

            if version == "1":
                time = anm.times[kf.timeindex]
                set_keyframe(curves_loc[bone_id], time * fps, kf.loc - loc_pos)
                set_keyframe(curves_rot[bone_id], time * fps, rot)
            elif version == "2":
                set_keyframe(curves_loc[bone_id], kf.frame & 0x7FFF, anm.translate[kf.tran_index] - loc_pos)
                set_keyframe(curves_rot[bone_id], kf.frame & 0x7FFF, rot)

    return act

def load(context, filepath, fps, version):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    try:
        if version == "1":
            anm = Anim_V1.open(filepath)
        elif version == "2":
            anm = Anim_V2.open(filepath)
    except InvalidAnimation:
        context.window_manager.popup_menu(invalid_file_format, title='Error', icon='ERROR')
        return {'CANCELLED'}

    arm_bones_num, anm_bones_num = len(arm_obj.pose.bones), len(anm.offsets[0])
    if arm_bones_num != anm_bones_num:
        context.window_manager.popup_menu(bones_number_mismatch, title='Error', icon='ERROR')

    animation_data = arm_obj.animation_data
    if not animation_data:
        animation_data = arm_obj.animation_data_create()

    bpy.ops.object.mode_set(mode='POSE')

    act = create_action(arm_obj, anm, fps, version)
    act.name = path.basename(filepath)
    animation_data.action = act

    context.scene.render.fps = 30

    max_frame = 0
    for fcu in act.fcurves:
        for kfp in fcu.keyframe_points:
            max_frame = max(max_frame, kfp.co[0])

    context.scene.frame_start = 0
    context.scene.frame_end = round(max_frame)

    bpy.ops.object.mode_set(mode='OBJECT')

    return {'FINISHED'}
