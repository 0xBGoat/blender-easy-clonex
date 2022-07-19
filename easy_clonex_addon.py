import bpy, os, zipfile
import bpy.utils.previews
from pathlib import Path
from bpy.types import Scene, Panel, PropertyGroup, Operator
from bpy.props import StringProperty, BoolProperty
from math import radians
from mathutils import Matrix
from . easybpy import *

BSDF_NODE_INDEX_DICT = {
    'BSDF_INPUT_BASE_COLOR_INDEX': 0,
    'BSDF_INPUT_METALLIC_INDEX': 6,
    'BSDF_INPUT_ROUGHNESS_INDEX': 9,
    'BSDF_INPUT_EMISSION_INDEX': 19,
    'BSDF_INPUT_NORMAL_INDEX': 22
}

def setup_viewport(context):
    # Move the camera into a better starting position
    mat_loc = Matrix.Translation((0, -10, 2))
    mat_sca = Matrix.Scale(1, 4, (1, 1, 1))
    mat_rot = Matrix.Rotation(radians(83), 4, 'X')
    mat_comb = mat_loc @ mat_rot @ mat_sca

    cam = bpy.data.objects['Camera']
    cam.data.lens = 112
    cam.matrix_world = mat_comb

    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            ctx = bpy.context.copy()
            ctx['area'] = area
            ctx['region'] = area.regions[-1]
            
            select_all_meshes()
            bpy.ops.view3d.view_selected()
            
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
            if get_image(path.name) is None:
                bpy.data.images.load(str(path.resolve()), check_existing=True)
                
                filename = path.stem
                
                tex_node = create_node(dna_nodes, "ShaderNodeTexImage")
                tex_node.image = get_image(path.name)
                
                tokens = filename.split('_')
                suffix = tokens[len(tokens)-1]
                
                if suffix == 'd':
                    # This is a base color image
                    output_socket = tex_node.outputs[0]
                    input_socket = dna_bsdf.inputs[BSDF_NODE_INDEX_DICT['BSDF_INPUT_BASE_COLOR_INDEX']]

                    if not input_socket.is_linked:
                        create_node_link(output_socket, input_socket)
                elif suffix == 'm':
                    # This is a metallic image
                    output_socket = tex_node.outputs[0]
                    input_socket = dna_bsdf.inputs[BSDF_NODE_INDEX_DICT['BSDF_INPUT_METALLIC_INDEX']]

                    if not input_socket.is_linked:
                        create_node_link(output_socket, input_socket)

                    tex_node.image.colorspace_settings.name = 'Non-Color'
                elif suffix == 'r':
                    # This is a roughness image
                    output_socket = tex_node.outputs[0]
                    input_socket = dna_bsdf.inputs[BSDF_NODE_INDEX_DICT['BSDF_INPUT_ROUGHNESS_INDEX']]

                    if not input_socket.is_linked:
                        create_node_link(output_socket, input_socket)
                    
                    tex_node.image.colorspace_settings.name = 'Non-Color'
                elif suffix == 'e':
                    # This is an emission image 
                    output_socket = tex_node.outputs[0]
                    input_socket = dna_bsdf.inputs[BSDF_NODE_INDEX_DICT['BSDF_INPUT_EMISSION_INDEX']]

                    if not input_socket.is_linked:
                        create_node_link(output_socket, input_socket)
                    
                    tex_node.image.colorspace_settings.name = 'Non-Color'
                elif suffix == 'n':
                    # This is a normal mapping image
                    # Need to create a normal map node between the texture image and BSDF node
                    normal_node = create_node(dna_nodes, "ShaderNodeNormalMap")
                    
                    normal_output_socket = normal_node.outputs[0]
                    input_socket = dna_bsdf.inputs[BSDF_NODE_INDEX_DICT['BSDF_INPUT_NORMAL_INDEX']]

                    if not input_socket.is_linked:
                        create_node_link(normal_output_socket, input_socket)
                    
                    create_node_link(tex_node.outputs[0], normal_node.inputs[1])
                    
                    tex_node.image.colorspace_settings.name = 'Non-Color'
                else:
                    # Not a valid texture image, remove both the image and the node
                    delete_image(tex_node.image)
                    delete_node(dna_nodes, tex_node)   
            
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
                else get_modifier(obj, 'Genesis8_1' + get_scene().clonex_gender.capitalize()))
            
            if armature_mod is not None:
                armature_mod.object = get_object('Genesis8_1' + get_scene().clonex_gender.capitalize())
        
    # Clean up unused objects          
    for obj in objects:
        if obj.type != 'MESH':
            delete_object(obj)   

def update_trait_selected(self, context):
    # Store the base_mats for comparison checks
    base_mats = [get_material('Head'), get_material('Suit')]
    
    print(self.trait_dir)
    if Path(os.path.join(self.trait_dir, '_' + get_scene().clonex_gender)).is_dir():
        filepath = os.path.join(self.trait_dir, '_' + get_scene().clonex_gender, '_blender')
    
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
        geo_objects = []  
        geo_object = None
        
        # These head and suit objects can have varying names, so do some fuzzy matching
        if Path(self.trait_dir).name.startswith('Characters'):
            geo_objects = get_objects_including('SuitGeo')
            filepath = os.path.join(self.trait_dir, '_textures', 'suit_' + get_scene().clonex_gender)
        elif Path(self.trait_dir).name.startswith('DNA'):
            geo_objects = get_objects_including('HeadGeo')
            filepath = os.path.join(self.trait_dir, '_texture')

        if len(geo_objects) > 0:
            geo_object = geo_objects[0]
        
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
    
class BaseCloneSelectOperator(Operator):
    """Use the file browser to select your base clone .blend file"""
    
    bl_idname = "clone_select.button"
    bl_label = "Select Location"

    directory: StringProperty(name="Directory", options={'HIDDEN'})
    filter_folder: BoolProperty(default=False, options={'HIDDEN'})
    
    def execute(self, context):                  
        # Delete the default cube if it exists
        if get_object("Cube") is not None:
            delete_object("Cube")
        
        # Load the base clone objects
        base_clone_path = None
        base_clone_filepath = None

        for path in Path(self.directory).iterdir():
            # Check to see if the directory already exists before unzipping
            if path.is_dir():
                if path.name.startswith('Characters-character'):
                    base_clone_path = path.resolve()
            else:
                if path.suffix == '.zip' and not Path(os.path.join(self.directory, path.stem)).is_dir():
                    # Unzip the file into a directoy with a matching name
                    with zipfile.ZipFile(path) as zip_ref:
                        zip_ref.extractall(os.path.join(self.directory, path.stem))
            
                    # Grab a reference to the base clone path
                    if path.stem.startswith('Characters-character'):
                        base_clone_path = os.path.join(self.directory, path.stem)

        if base_clone_path is not None:
            base_clone_path = os.path.join(base_clone_path, '_' + get_scene().clonex_gender, '_blender')
            base_clone_file = os.listdir(base_clone_path)[0]
            base_clone_filepath = os.path.join(base_clone_path, base_clone_file)

            with bpy.data.libraries.load(base_clone_filepath) as (data_from, data_to):
                data_to.objects = data_from.objects
                
        if not collection_exists("Character"):
            create_collection("Character")
            link_objects_to_collection(data_to.objects, get_collection("Character"))    
            
        get_scene().clonex_trait_collection.clear()
        
        for i in range(len([f for f in os.listdir(self.directory) if os.path.isdir(os.path.join(self.directory, f))])):
            folder_name = [f for f in os.listdir(self.directory) if os.path.isdir(os.path.join(self.directory, f))][i]
            
            # Don't create a checkbox for the base clone file
            if 'Characters-character' in folder_name or not folder_name.endswith('Combined'):
                continue

            trait_display_name = format_trait_display_name(folder_name)
                    
            item = get_scene().clonex_trait_collection.add()
            item.trait_dir = os.path.join(self.directory, folder_name)
            item.trait_name = trait_display_name
            
            # Only equip one of the bottoms initially
            if 'Bottoms - Tech' in trait_display_name or 'Bottoms - Leggings' in trait_display_name:
                item.trait_selected = False
            else: 
                item.trait_selected = True
        
        get_scene().clonex_loaded = True
        setup_viewport(context)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

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

        # Row for gender selection
        row_gender_heading = layout.row()
        row_gender_heading.label(text="Select Clone Gender")

        row_gender_buttons = layout.row()
        row_gender_buttons.scale_y = 1.5
        row_gender_buttons.prop(get_scene(), 'clonex_gender', expand=True)
       
        # Row for Clone select button
        row_button = layout.row()
        row_button.scale_y = 1.5
        row_button.enabled = True
        row_button.active = True
        row_button.operator(BaseCloneSelectOperator.bl_idname, text='Open CloneX 3D Files', depress=True, emboss=True, icon='FILE_FOLDER')
        
        if get_scene().clonex_loaded == True:
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
            col_traits.alignment = 'Expand'.upper()
            
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