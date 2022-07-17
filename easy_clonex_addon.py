import bpy, os
import bpy.utils.previews
from pathlib import Path
from bpy_extras.io_utils import ImportHelper
from bpy.types import Scene, Panel, PropertyGroup, Operator
from bpy.props import StringProperty
from . easybpy import *

def set_material_preview_shading():    
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'

def apply_dna_textures_to_object(filepath, geo_object):
    base_mat = get_material_from_object(geo_object)
    
    dna_mat_name = 'Dna_Head' if base_mat.name == 'Head' else 'Dna_Suit'   
    dna_mat = get_material(dna_mat_name)
    
    if dna_mat is None:
        dna_mat = create_material(dna_mat_name)
        dna_mat.use_nodes = True

        dna_nodes = get_nodes(dna_mat)
        dna_bsdf = get_node(dna_nodes, 'Principled BSDF')
        dna_bsdf.subsurface_method = 'BURLEY'
        
        # Load all of the image files
        image_exts = ['.png', '.jpg', '.jpeg']

        for path in [p for p in Path(filepath).rglob('*') if p.suffix in image_exts]:
            bpy.data.images.load(str(path.resolve()), check_existing=True)
            
            filename = path.stem
            
            tex_node = create_node(dna_nodes, "ShaderNodeTexImage")
            tex_node.image = get_image(path.name)
            
            tokens = filename.split('_')
            suffix = tokens[len(tokens)-1]
            
            match suffix:
                case 'd':
                    # This is a base color image
                    create_node_link(tex_node.outputs[0], dna_bsdf.inputs[0])
                case 'm':
                    # This is a metallic image
                    create_node_link(tex_node.outputs[0], dna_bsdf.inputs[6])
                    tex_node.image.colorspace_settings.name = 'Non-Color'
                case 'r':
                    # This is a roughness image
                    create_node_link(tex_node.outputs[0], dna_bsdf.inputs[9])
                    tex_node.image.colorspace_settings.name = 'Non-Color'
                case 'n':
                    # This is a normal mapping image
                    # Need to create a normal map node between the texture image and BSDF node
                    normal_node = create_node(dna_nodes, "ShaderNodeNormalMap")
                    create_node_link(normal_node.outputs[0], dna_bsdf.inputs[22])
                    create_node_link(tex_node.outputs[0], normal_node.inputs[1])
                    tex_node.image.colorspace_settings.name = 'Non-Color'
                case 'e':
                    # This is an emission image 
                    create_node_link(tex_node.outputs[0], dna_bsdf.inputs[19])
                    tex_node.image.colorspace_settings.name = 'Non-Color'
                case _:
                    print('Unhandled image type')       
            
        # Add the new material to the geo_object       
        add_material_to_object(geo_object, dna_mat)
    
    # Swap the material_slots for the base and dna materials
    geo_object.material_slots[0].material = dna_mat
    geo_object.material_slots[len(geo_object.material_slots)-1].material = base_mat
    
def remove_dna_textures_from_object(geo_object):
    base_mat = geo_object.material_slots[len(geo_object.material_slots)-1]
    base_mat_name = 'Head' if base_mat.name == 'Head' else 'Suit'
    
    if geo_object.material_slots[0].material.name != get_material(base_mat_name).name:
        base_mat = get_material(base_mat_name)
        dna_mat = geo_object.material_slots[0].material
        
        geo_object.material_slots[0].material = base_mat
        geo_object.material_slots[len(geo_object.material_slots)-1].material = dna_mat

def load_clonex_trait_files_into_collection(trait_collection, filepath):
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        data_to.objects = data_from.objects
                            
    link_objects_to_collection(data_to.objects, trait_collection)
    
    # Get all mesh objects from the collection and update their Armature modifiers
    objects = get_objects_from_collection(trait_collection)
    
    for obj in objects:
        if obj.type == 'MESH':
            # Clear the parent, then update the armature modifier
            select_only(obj)
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            
            armature_mod = (get_modifier(obj, 'Armature') 
                if get_modifier(obj, 'Armature') 
                else get_modifier(obj, 'Genesis8_1' + Scene.clonex_gender.capitalize()))
            
            if armature_mod is not None:
                armature_mod.object = get_object('Genesis8_1' + Scene.clonex_gender.capitalize())
        
    # Clean up unused objects          
    for obj in objects:
        if obj.type != 'MESH':
            delete_object(obj)   

def update_trait_selected(self, context):
    abs_trait_dir = os.path.join(Scene.clonex_home_dir, self.trait_dir)
    
    # Store the base_mats for comparison checks
    base_mats = [get_material('Head'), get_material('Suit')]
    
    if Path(os.path.join(abs_trait_dir, '_' + Scene.clonex_gender)).is_dir():
        filepath = os.path.join(abs_trait_dir, '_' + Scene.clonex_gender + '\_blender')
    
        for file in os.listdir(filepath):
            if file.endswith('.blend'):
                # Append the objects from blend file              
                if self.trait_selected:
                    if not collection_exists(self.trait_name):
                        # This is the first time the trait is being selected so load the files
                        trait_collection = create_collection(self.trait_name)
                        load_clonex_trait_files_into_collection(trait_collection, os.path.join(filepath, file))
                                                                 
                    else:
                        # If the collection already exists just unhide it
                        unhide_collection_viewport(self.trait_name)
                        unhide_collection_render(self.trait_name)
                else:
                    if collection_exists(self.trait_name):
                        hide_collection_viewport(self.trait_name)
                        hide_collection_render(self.trait_name)
                    
                break
    else:
        # These traits are textures that need to be applied
        filepath = ''  
        geo_object = None
        
        if self.trait_dir.startswith('Characters'):
            geo_object = get_object('CloneX_' + Scene.clonex_gender.capitalize() + '_SuitGeo')
            filepath = os.path.join(abs_trait_dir, '_textures\suit_' + Scene.clonex_gender)
        elif self.trait_dir.startswith('DNA'):
            geo_object = get_object('CloneX_HeadGeo')
            filepath = os.path.join(abs_trait_dir, '_texture')
        
        geo_mat = get_material_from_object(geo_object)

        if geo_object is not None:
            if self.trait_selected and geo_mat in base_mats:
                apply_dna_textures_to_object(filepath, geo_object)
            elif not self.trait_selected and geo_mat not in base_mats:       
                remove_dna_textures_from_object(geo_object)
            else:
                print('Material state is out of sync, no action taken')

def format_trait_display_name(folder_name):
    folder_name_tokenized = folder_name.split('-')
    trait_name = ''
    
    for idx, token in enumerate(folder_name_tokenized):
        if idx == 0:
            trait_name += token + ' -'
            continue
        
        if (token != 'Combined'):
            trait_description_tokens = token.split('_')
            
            for desc_token in trait_description_tokens:
                trait_name += ' ' + desc_token.capitalize()

    return trait_name 
    
class BaseCloneSelectOperator(Operator, ImportHelper):
    """Use the file browser to select your base clone .blend file"""
    
    bl_idname = "clone_select.button"
    bl_label = "Open Clone"
    
    filter_glob: StringProperty(
        default='*.blend',
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        filepath = Path(self.filepath)
        filename = filepath.name
        
        # Detect gender and store it in a Scene prop 
        Scene.clonex_gender = 'male' if filename.startswith('m') else 'female'
        
        # Delete the default cube if it exists
        if get_object("Cube") is not None:
            delete_object("Cube")
        
        # Load the base clone objects
        with bpy.data.libraries.load(str(filepath)) as (data_from, data_to):
            data_to.objects = data_from.objects
            
        if not collection_exists("Character"):
            create_collection("Character")
            link_objects_to_collection(data_to.objects, get_collection("Character"))    
            
        # Find the location of all trait folders relative to base clone file
        clonex_dir = filepath.parents[3]
        Scene.clonex_home_dir = clonex_dir
        
        get_scene().clonex_trait_collection.clear()
        
        for i in range(len([f for f in os.listdir(clonex_dir) if os.path.isdir(os.path.join(clonex_dir, f))])):
            folder_name = [f for f in os.listdir(clonex_dir) if os.path.isdir(os.path.join(clonex_dir, f))][i]
            
            # Ignore the current file
            if 'character_neutral' in folder_name:
                continue
                       
            item = get_scene().clonex_trait_collection.add()
           
            item.trait_dir = folder_name
            item.trait_name = format_trait_display_name(folder_name)
            item.trait_selected = False
        
        Scene.clonex_loaded = True
        set_material_preview_shading()
        
        return {'FINISHED'}

class EasyCloneXPanel(Panel):
    bl_label = 'Easy CloneX'
    bl_idname = 'OBJECT_PT_easy_clonex'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = ''
    bl_category = 'CloneX'
    bl_order = 0
    bl_ui_units_x = 0
    
    @classmethod
    def poll(cls, context):
        return not (False)
    
    def draw_header(self, context):
        layout = self.layout
        
    def draw(self, context):
        layout = self.layout
        
        # Row for Clone select button
        row_button = layout.row()
        row_button.scale_y = 1.5
        row_button.enabled = True
        row_button.active = True
        row_button.operator(BaseCloneSelectOperator.bl_idname, text='Open Base Clone', depress=True, emboss=True, icon='FILE_BLEND')
        
        if Scene.clonex_loaded == True:
            layout.separator(factor=1.0)
            
            row_trait_heading = layout.row()
            row_trait_heading.label(text='Select Traits')
            
            # Column for displaying Traits with checkboxes
            col_traits = layout.box()
            col_traits.alert = False
            col_traits.enabled = True
            col_traits.active = True
            col_traits.use_property_split = False
            col_traits.use_property_decorate = False
            col_traits.scale_x = 1.0
            col_traits.scale_y = 1.0
            col_traits.alignment = 'Expand'.upper() # Why is this call to upper necessary?
            
            for i in range(len(get_scene().clonex_trait_collection)):
                col_traits.prop(
                    get_scene().clonex_trait_collection[i], 
                    'trait_selected', 
                    text=get_scene().clonex_trait_collection[i].trait_name, 
                    icon_value=0, 
                    emboss=True, 
                    expand=True
                )
        
class CloneXTraitPropertyGroup(PropertyGroup):
    trait_dir: bpy.props.StringProperty(name='Trait Directory', description='', default='', subtype='NONE', maxlen=0)
    trait_name: bpy.props.StringProperty(name='Trait Name', description='', default='', subtype='NONE', maxlen=0)
    trait_selected: bpy.props.BoolProperty(name='Trait Selected', description='', default=False, update=update_trait_selected) 