import bpy
from dataclasses import dataclass
from mathutils import Quaternion, Vector
from .anm import Anim_V1, Keyframe, Anim_V2, Keyframe_V2


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to export animation')


def missing_action(self, context):
    self.layout.label(text='No action for active armature. Nothing to export')


@dataclass
class PoseBoneTransform:
    pos: Vector
    rot: Quaternion

    def calc_kf(self, mat):
        kf_pos = self.pos + mat.to_translation()
        kf_rot = mat.inverted_safe().to_quaternion().rotation_difference(self.rot).normalized()
        return kf_pos, kf_rot


def get_bone_transform(pose_bone):
    pos = pose_bone.location.copy()
    if pose_bone.rotation_mode == 'QUATERNION':
        rot = pose_bone.rotation_quaternion.copy()
    else:
        rot = pose_bone.rotation_euler.to_quaternion()
    return PoseBoneTransform(pos, rot)


def get_action_range(arm_obj, act):
    frame_start, frame_end = None, None

    for curve in act.fcurves:
        if 'pose.bones' not in curve.data_path:
            continue

        bone_name = curve.data_path.split('"')[1]
        if arm_obj.data.bones.find(bone_name) is None:
            continue

        for kp in curve.keyframe_points:
            time = kp.co[0]
            if frame_start is None:
                frame_start, frame_end = time, time
            else:
                frame_start = min(frame_start, time)
                frame_end = max(frame_end, time)

    return int(frame_start), round(frame_end)
    

def has_keyframe(action, bone, frame_number):
    for fcurve in action.fcurves:
        if bone.name in fcurve.data_path:
            for keyframe in fcurve.keyframe_points:
                if int(keyframe.co.x) == frame_number:
                    return True
    return False


def create_anm(context, arm_obj, act, fps, flags, version):
    offsets, keyframes, times, translate = [], [], [], []

    old_frame = context.scene.frame_current
    frame_start, frame_end = get_action_range(arm_obj, act)
    bone_transforms = {}

    if frame_start is None:
        return None

    context.scene.frame_set(frame_start)
    context.view_layer.update()

    has_keyframe_dict = {}
    for frame in range(frame_start, frame_end+1):
        context.scene.frame_set(frame)
        context.view_layer.update()

        has_keyframe_dict[frame] = [has_keyframe(act, bone, frame) for bone in arm_obj.pose.bones]
        if not any(has_keyframe_dict[frame]):
            continue

        for bone_id, pose_bone in enumerate(arm_obj.pose.bones):
            if frame == frame_start:
                bone_transforms[bone_id] = [get_bone_transform(pose_bone)]
            else:
                bone_transforms[bone_id].append(get_bone_transform(pose_bone))

        offsets.append([])
        times.append(frame - frame_start)    

    for bone_id, transforms in sorted(bone_transforms.items()):
        bone = arm_obj.data.bones[bone_id]

        loc_mat = bone.matrix_local.copy()
        if bone.parent:
            loc_mat = bone.parent.matrix_local.inverted_safe() @ loc_mat

        for time_id, (frame, trans) in enumerate(zip(times, transforms)):
            if bone.name == "unnamed" and 0 < time_id < len(transforms)-1:
                offsets[time_id].append(len(keyframes) - 1)
                continue

            if time_id == 0 or time_id == len(transforms)-1 or has_keyframe_dict[frame][bone_id]:
                kf_pos, kf_rot = trans.calc_kf(loc_mat)             
                if version == "1":
                    keyframes.append(Keyframe(time_id, kf_rot, kf_pos))
                elif version == "2":
                    if kf_pos not in translate:
                        translate.append(kf_pos)
                    keyframes.append(Keyframe_V2(frame, translate.index(kf_pos), kf_rot))            
            offsets[time_id].append(len(keyframes) - 1)

    offsets.pop()
    context.scene.frame_set(old_frame)
    context.view_layer.update()

    if version == "1":
        return Anim_V1(flags, keyframes, [t / fps for t in times], offsets)
    elif version == "2":
        return Anim_V2(keyframes, times, translate, offsets)


def save(context, filepath, fps, flags, endian, version):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    act = None
    animation_data = arm_obj.animation_data
    if animation_data:
        act = animation_data.action

    anm = None
    if act:
        anm = create_anm(context, arm_obj, act, fps, flags, version)

    if not anm:
        context.window_manager.popup_menu(missing_action, title='Error', icon='ERROR')
        return {'CANCELLED'}

    anm.save(filepath, endian)

    return {'FINISHED'}
