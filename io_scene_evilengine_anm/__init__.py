import bpy
from bpy.props import (
        CollectionProperty,
        EnumProperty,
        FloatProperty,
        IntProperty,
        StringProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        )
from pathlib import Path

bl_info = {
    "name": "EvilEngine Animation",
    "author": "Psycrow, EnergyDrink",
    "version": (0, 2, 0),
    "blender": (2, 81, 0),
    "location": "File > Import-Export",
    "description": "Import / Export EvilEngine Animation (.anm)",
    "warning": "",
    "wiki_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"
}

import sys
from importlib import import_module
if __name__ in sys.modules:
    module_to_reload = [module_name for module_name in sys.modules if module_name.startswith(__name__) and module_name != __name__]
    for module_name in module_to_reload:
        del sys.modules[module_name]
        import_module(module_name)
        print(f"Reloaded module: {module_name}")


VERSION1_GAMES = "-Scooby-Doo: Night of 100 Frights\n-SpongeBob SquarePants: Battle for Bikini Bottom\n-The SpongeBob SquarePants Movie\n-The Incredibles"
VERSION2_GAMES = "-The Incredibles: Rise of The Underminer\n-Ratatouille Prototype"


class ImportEvilAnm(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.evil_anm"
    bl_label = "Import Animation"
    bl_description = "Imports a binary evilengine animation file (SKB1)"
    bl_options = {'PRESET', 'UNDO'}

    filter_glob: StringProperty(default="*.anm", options={'HIDDEN'})
    filename_ext = ".anm"

    fps: FloatProperty(
        name="FPS",
        description="Value by which the keyframe time is multiplied",
        default=30.0,
    )

    version: EnumProperty(
        name="Version",
        description="Animation Version",
        items={
            ("1", "1", VERSION1_GAMES),
            ("2", "2", VERSION2_GAMES)
        },
        default="1",
    )

    files: CollectionProperty(type=bpy.types.PropertyGroup)

    def execute(self, context):
        from . import import_evil_anm

        files_dir = Path(self.filepath)
        for selection in self.files:
            file_path = Path(files_dir.parent, selection.name)
            if file_path.suffix.lower() == self.filename_ext:
                import_evil_anm.load(context, file_path, self.fps, self.version)
        return {'FINISHED'}


class ExportEvilAnm(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.evil_anm"
    bl_label = "Export Animation"
    bl_description = "Exports a binary evilengine animation file (SKB1)"
    bl_options = {'PRESET'}

    filter_glob: StringProperty(default="*.anm", options={'HIDDEN'})
    filename_ext = ".anm"

    fps: FloatProperty(
        name="FPS",
        description="Value by which the keyframe time is divided, only available in version 1",
        default=30.0,
    )

    endian: EnumProperty(
        name="Platform",
        description="Target console (byte order)",
        items={
            ('<', 'PS2/Xbox', 'Little-Endian'),
            ('>', 'GameCube', 'Big-Endian')},
        default='>',
    )

    version: EnumProperty(
        name="Version",
        description="Animation Version",
        items={
            ("1", "1", VERSION1_GAMES),
            ("2", "2", VERSION2_GAMES)
        },
        default="1",
    )

    flags: IntProperty(
        name="Flags",
        description="Animation flags, only available in Version 1",
        default=0,
    )

    def execute(self, context):
        from . import export_evil_anm

        return export_evil_anm.save(context, self.filepath, self.fps, self.flags, self.endian, self.version)
    
def menu_func_import(self, context):
    self.layout.operator(ImportEvilAnm.bl_idname,
                         text="EvilEngine Animation (.anm)")


def menu_func_export(self, context):
    self.layout.operator(ExportEvilAnm.bl_idname,
                         text="EvilEngine Animation (.anm)")

classes = (
    ImportEvilAnm,
    ExportEvilAnm,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
