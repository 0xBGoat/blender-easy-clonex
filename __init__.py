bl_info = {
    "name": "Easy CloneX",
    "author": "OxBGoat",
    "version": (0, 3, 0),
    "blender": (3, 2, 0),
    "description": "An Add-on that makes it easy to assemble a Clone from CloneX 3D files",
    "category": "CloneX"
}

import bpy

from bpy.types import Scene
from bpy.props import PointerProperty
from bpy.utils import register_class, unregister_class
from . import easy_clonex_addon as eca

classes = (
    eca.EC_UL_TraitList,
    eca.CloneXTraitPropertyGroup,
    eca.EasyCloneXAddOnPropertyGroup,
    eca.EC_OT_CloneSelectOperator,
    eca.EC_OT_ExportOperator,
    eca.EC_OT_MixamoButton,
    eca.EC_PT_MainPanel,
    eca.EC_PT_TraitsPanel,
    eca.EC_PT_AdvancedPanel
)

def register():    
    for cls in classes:
        register_class(cls)

    Scene.addon_properties = PointerProperty(name='Easy CloneX Add-on Properties', type=eca.EasyCloneXAddOnPropertyGroup)

def unregister():
    for cls in classes:
        unregister_class(cls)
    
    del Scene.addon_properties
    
if __name__ == "__main__":
    register()