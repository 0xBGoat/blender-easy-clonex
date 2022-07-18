bl_info = {
    "name": "Easy CloneX",
    "author": "OxBGoat",
    "version": (0, 1, 5),
    "blender": (3, 2, 0),
    "description": "An Add-on that makes it easy to assemble a Clone from CloneX 3D files",
    "category": "CloneX"
}

import bpy

from bpy.types import Scene
from bpy.props import (StringProperty, BoolProperty, CollectionProperty)
from bpy.utils import register_class, unregister_class
from . import easy_clonex_addon as eca

def register():
    global _icons
    _icons = bpy.utils.previews.new()
    
    register_class(eca.BaseCloneSelectOperator)
    register_class(eca.CloneXTraitPropertyGroup)

    Scene.clonex_trait_collection = CollectionProperty(name='Trait Collection', description='', type=eca.CloneXTraitPropertyGroup)
    Scene.clonex_home_dir = StringProperty(name='CloneX Home Dir', description='', default='', subtype='NONE', maxlen=0)
    Scene.clonex_gender = StringProperty(name='CloneX Gender', description='', default='male', subtype='NONE', maxlen=0)
    Scene.clonex_loaded = BoolProperty(name='CloneX Loaded', description='', default=False)
    
    try: 
        register_class(eca.EasyCloneXPanel)
    except:
        pass    

def unregister():
    global _icons
    bpy.utils.previews.remove(_icons)
    
    del Scene.clonex_trait_collection
    del Scene.clonex_home_dir
    del Scene.clonex_gender
    del Scene.clonex_loaded
    
    unregister_class(eca.CloneXTraitPropertyGroup)
    unregister_class(eca.BaseCloneSelectOperator)
    
    try: 
        unregister_class(eca.EasyCloneXPanel)
    except: 
        pass
    
if __name__ == "__main__":
    register()