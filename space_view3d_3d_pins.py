# ##### BEGIN GPL LICENSE BLOCK #####
#
#   Blender Buttons and Menu Pinning Addon
#   Copyright (C) 2014 Morshidul Chowdhury (iPLEOMAX)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Buttons and Menu Pinning",
    "author": "Morshidul Chowdhury (iPLEOMAX)",
    "version": (1, 1, 0),
    "blender": (2, 7, 1),
    "location": "3D View > Toolbar > Pins",
    "warning": "Pins need to be re-enabled when changing Screens.",
    "description": "Pin buttons and menus in 3d View for quick access",
    "category": "3D View"
}

import bpy
import bgl
import blf
import os.path
import pickle
from bpy.props import *
from time import time
from random import randint
from bpy.app.handlers import persistent

def active_preset_id(context):
    wm = context.window_manager
    if not len(wm.pins_presets):
        return "0"
    preset = wm.pins_presets[wm.pins_presets_active_index]
    return preset.id

def save_pins(context):
    wm = context.window_manager
    
    data = {}
    data['version'] = bl_info["version"]
    data['pins_enabled'] = wm.pins_enabled
    data['pins_opacity'] = wm.pins_opacity
    data['pins_presets_active_index'] = wm.pins_presets_active_index
    data['pins'] = []
    for pin in wm.pins_data:
        pin_dict = {}
        for k in pin.keys():
            pin_dict[k] = getattr(pin, k)
        data['pins'].append(pin_dict)
    data['presets'] = []
    for preset in wm.pins_presets:
        preset_dict = {}
        for k in preset.keys():
            preset_dict[k] = getattr(preset, k)
        data['presets'].append(preset_dict)
            
    file_path = bpy.app.tempdir + "blender_pins.dat"
    pickle.dump(data, open(file_path, "wb"), protocol=pickle.HIGHEST_PROTOCOL)
    
    #print("[Pins] Saved %i pin(s), %i preset(s)." % (len(data['pins']), len(data['presets'])))

def load_pins(context):

    file_path = bpy.app.tempdir + "blender_pins.dat"
    if not os.path.isfile(file_path):
        return
 
    data = pickle.load(open(file_path, "rb"))
    
    if data.get('version') != bl_info["version"]:
        print("[Pins] Existing pins data is incompatible, loading cancelled.")
        return
    
    wm = context.window_manager
    
    try:
        wm.pins_opacity = float(data.get('pins_opacity'))
        wm.pins_presets_active_index = data.get('pins_presets_active_index')
    except:
        pass
    
    pins = data.get('pins')
    if pins:
        for pin in pins:
            new_pin = wm.pins_data.add()
            for k in pin:
                if hasattr(new_pin, k):
                    setattr(new_pin, k, pin[k])
            
    presets = data.get('presets')
    if presets:
        for preset in presets:
            new_preset = wm.pins_presets.add()
            for k in preset:
                if hasattr(new_preset, k):
                    setattr(new_preset, k, preset[k])
    
    if data.get('pins_enabled') is True:
        wm.pins_invoke = True
    
    wm.pins_loaded = True
    print("[Pins] Loaded %i pin(s), %i preset(s)." % (len(pins), len(presets)))
        
def draw_pin(text, mx, my, bx, by, w, h, t, f):
    dFont = 0
    bx -= w/2
    bx2 = bx + w
    by2 = by - h/2
    by += h/2
    
    if bx <= mx <= bx2 and by2 <= my <= by: hover = True
    else: hover = False
    
    if hover: col = bpy.context.user_preferences.themes[0].user_interface.wcol_menu_item.inner_sel
    else: col = bpy.context.user_preferences.themes[0].user_interface.wcol_menu.inner_sel
    if f: col = [1.0, 0.0, 0.0]
    dR = col[0]
    dG = col[1]
    dB = col[2]
    dA = bpy.context.window_manager.pins_opacity
    
    positions = [[bx, by], [bx2, by], [bx2, by2], [bx, by2]]
    settings = [[bgl.GL_LINE_LOOP, 0.8], [bgl.GL_QUADS, dA]]
    for mode, box_alpha in settings:
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBegin(mode)
        bgl.glColor4f(dR, dG, dB, box_alpha)
        for v1, v2 in positions:
            bgl.glVertex2f(v1, v2)
        bgl.glEnd()
        
    blf.size(dFont, 12, 72)
    blf.position(dFont, bx + 12, by - 14, 0)
    dR = 1.0
    dG = 1.0
    dB = 1.0
    dA = 1.0
    bgl.glColor4f(dR, dG, dB, dA)
    blf.draw(dFont, text)
    
    if t == 0:
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBegin(bgl.GL_TRIANGLES)
        dA = 0.4
        bgl.glColor4f(dR, dG, dB, dA)
        if by > 100: arrow = [[bx + 109, by - 7], [bx + 112.5, by - 14], [bx + 116, by - 7]]
        else: arrow = [[bx + 109, by - 13], [bx + 112.5, by - 6], [bx + 116, by - 13]]
        for v1, v2 in arrow:
            bgl.glVertex2f(v1, v2)
        bgl.glEnd()
    
    return hover

def find_parent(childid, x, y, w, h, context):
    align = 0
    parent = "0"
    for pin in context.window_manager.pins_data:
        if pin.preset != active_preset_id(context): continue
        if pin.id == childid: continue
        if pin.parent == childid: continue
        
        bx = pin.x * w
        by = pin.y * h
        
        if by + 11 >= y >= by - 11:
            if bx - 110 <= x <= bx - 60: 
                align = 2
                parent = pin.id
            elif bx + 60 <= x <= bx + 110:
                align = 3
                parent = pin.id
        elif bx - 59 <= x <= bx + 59:
            if by + 11 <= y <= by + 30:
                align = 1
                parent = pin.id
            elif by - 11 >= y >= by - 30:
                align = 0
                parent = pin.id

    return [parent, align]

def get_parent_pos(context, id):
    for pin in context.window_manager.pins_data:
        if pin.id == id:
            return [pin.x, pin.y]
    return [0, 0]
    
def draw_callback_px(self, context):
    if context.area.type != 'VIEW_3D': return
    if context.region.id != VIEW3D_OT_pins._region_id: return
    
    wm = context.window_manager
    x = self.cursor[0]
    y = self.cursor[1]
    
    for i, pin in enumerate(wm.pins_data):
        if pin.preset != active_preset_id(context): continue
        
        if not pin.set:
            pin.x = x / context.region.width
            pin.y = y / context.region.height
            
            parent = find_parent(pin.id, x, y, context.region.width, context.region.height, context)
            pin.parent = parent[0]
            pin.align = parent[1]
            
        if pin.parent != "0":
            pos = get_parent_pos(context, pin.parent)
            if pin.align == 0: #bottom
                drawx = pos[0] * context.region.width
                drawy = pos[1] * context.region.height - 24
            elif pin.align == 1: #up
                drawx = pos[0] * context.region.width
                drawy = pos[1] * context.region.height + 24
            elif pin.align == 2: #left
                drawx = pos[0] * context.region.width - 123
                drawy = pos[1] * context.region.height
            elif pin.align == 3: #right
                drawx = pos[0] * context.region.width + 123
                drawy = pos[1] * context.region.height
            pin.x = drawx / context.region.width
            pin.y = drawy / context.region.height
        
        if pin.type == 0:
            if not pin.call.startswith('INFO'):
                if pin.mode != context.mode: continue
        
        bx = pin.x * context.region.width
        by = pin.y * context.region.height
        
        length = len(pin.text)
        if length > 16:
            display_text = '%s..%s' % (pin.text[:8], pin.text[-8:])
        elif length > 14:
            display_text = '%s..' % pin.text[:15]
        else:
            display_text = pin.text
            
        if(draw_pin(display_text, x, y, bx, by, 120, 22, pin.type, pin.failed)):
            self.hover = i
        pin.failed = False
    
class VIEW3D_OT_pins(bpy.types.Operator):
    bl_idname = "view3d.pins"
    bl_label = "Pins"
    bl_description = "Draw pins over 3D View"
    
    _handle = None
    _region_id = None
    
    @staticmethod
    def handle_add(self, context):
        self.cursor = [0, 0]
        self.hover = -1
        VIEW3D_OT_pins._region_id = context.region.id
        VIEW3D_OT_pins._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL')
        
    @staticmethod
    def handle_remove(context):
        if VIEW3D_OT_pins._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(VIEW3D_OT_pins._handle, 'WINDOW')
        VIEW3D_OT_pins._handle = None
        VIEW3D_OT_pins._region_id = None
    
    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            self.cursor = [event.mouse_region_x, event.mouse_region_y]
        
        wm = context.window_manager
        
        if self.hover != -1:
            id = self.hover
            self.hover = -1
            if event.type == 'RIGHTMOUSE':
                if event.value == 'PRESS':
                    wm.pins_data[id].set = not wm.pins_data[id].set
                    if wm.pins_data[id].set:
                        save_pins(context)
                return {'RUNNING_MODAL'}
            if event.type == 'LEFTMOUSE':
                if event.value == 'RELEASE':
                    pin = wm.pins_data[id]
                    if pin.set:
                        if pin.type == 0: #Menu
                            bpy.ops.wm.call_menu(name=pin.call)
                        else:
                            try:
                                result = eval(pin.call)
                                if result not in [{'FINISHED'}, {'RUNNING_MODAL'}]:
                                    pin.failed = True
                            except:
                                pin.failed = True
                return {'RUNNING_MODAL'}
        
        if not context.window_manager.pins_enabled:
            VIEW3D_OT_pins.handle_remove(context)
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
    def cancel(self, context):
        if context.window_manager.pins_enabled:
            VIEW3D_OT_pins.handle_remove(context)
            context.window_manager.pins_enabled = False
    
    def invoke(self, context, event):
        wm = context.window_manager
        if context.area.type == 'VIEW_3D':
            if wm.pins_enabled is False:
                wm.pins_enabled = True
                VIEW3D_OT_pins.handle_add(self, context)
                wm.modal_handler_add(self)
                save_pins(context)
                return {'RUNNING_MODAL'}
            else:
                wm.pins_enabled = False
                save_pins(context)
                return {'CANCELLED'}
        else:
            self.report({'WARNING'}, "No 3D Views were found, cannot run pins.")
            return {'CANCELLED'}

def build_operator(op):
    op_dir = "bpy.ops.%s" % (".".join(op.bl_idname.lower().split("_ot_", 1)))
    op_args = "("
    
    for i, k in enumerate(op.properties.keys()):
        if hasattr(op.properties, k):
            if i != 0: op_args += ", "
            attr = getattr(op.properties, k)
            if isinstance(attr, str):
                op_args += "%s='%s'" % (k, attr)
            elif isinstance(attr,(type(None),int,float,bool)):
                op_args += "%s=%s" % (k, attr)
            else:
                if hasattr(bpy.types, k) is False:
                    op_args += "%s=%s" % (k, tuple(attr))
                else:
                    op_args += "%s={" % k
                    for ni, nk in enumerate(attr.bl_rna.properties.keys()):
                        if hasattr(attr, nk):
                            if nk == 'rna_type': continue
                            if ni > 1: op_args += ", "
                            nattr = getattr(attr, nk)
                            if isinstance(nattr, str):
                                value = "'%s'" % nattr
                            elif isinstance(nattr, (type(None),int,float,bool)):
                                value = str(nattr)
                            else:
                                value = str(tuple(nattr))
                            op_args += "\"%s\":%s" % (nk, value)
                    op_args += "}"
                    
    op_args += ")"
    return "%s%s" % (op_dir, op_args)
            
class VIEW3D_OT_pins_add_operator(bpy.types.Operator):
    bl_idname = "view3d.pins_add_operator"
    bl_label = "Add operator pin"
    bl_description = "Adds a new operator pin"

    text = StringProperty("Pin Text", default="Pin")
    last_op_id = IntProperty("Last operator ID", default = -1)
    with_pars = BoolProperty("With parameters", default=True)
    
    def execute(self, context):
        if not context.window_manager.pins_enabled:
            bpy.ops.view3d.pins('INVOKE_DEFAULT')
            
        wm = context.window_manager
        
        if not len(wm.pins_presets):
            bpy.ops.view3d.pins_preset_add('INVOKE_DEFAULT')
        
        new_pin = wm.pins_data.add()
        new_pin.id = "%s%i" % (str(time()).replace('.',''), randint(0, 1000))
        new_pin.text = self.text
        new_pin.type = 1
        
        op_func = build_operator(wm.operators[self.last_op_id])
        if self.with_pars:
            if op_func.endswith("()"):
                op_func = op_func.replace("()", "(True)")
            else:
                op_func = op_func.replace("(", "(True, ", 1)
        else:
            op_func = op_func[:op_func.find("(")]
            op_func += "('INVOKE_DEFAULT', True)"
        
        print(op_func)
        new_pin.call = op_func
        new_pin.preset = active_preset_id(context)
        
        save_pins(context)
        return {'FINISHED'}
    
class VIEW3D_PT_pins(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_pins"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Pins"
    
    bl_label = "Configure"
    
    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        
        if wm.pins_enabled is False:
            layout.operator(VIEW3D_OT_pins.bl_idname, 'Show Pins', icon='UNPINNED')
        else:
            layout.operator(VIEW3D_OT_pins.bl_idname, 'Hide Pins', icon='PINNED')
        
        layout.prop(wm, 'pins_opacity', text='Opacity')

        if len(wm.operators):
            layout.label("Name of new pin:")
            layout.prop(wm, 'pins_text', text="")
            layout.prop(wm, 'pins_with_pars', text="With parameters")
            layout.label("Pin last used operators:")
            col = layout.column()
            sub = col.column(align=True)
            for i, op in reversed(list(enumerate(wm.operators))[-5:]):
                props = sub.operator(VIEW3D_OT_pins_add_operator.bl_idname, icon='PLUS', text=op.name)
                if not len(wm.pins_text):
                    props.text = op.name
                else:
                    props.text = wm.pins_text
                props.last_op_id = i
                props.with_pars = context.window_manager.pins_with_pars
        else:
            layout.label("No operator history.")
        
class VIEW3D_OT_pins_preset_add(bpy.types.Operator):
    bl_idname = "view3d.pins_preset_add"
    bl_label = "Add preset"
    bl_description = "Adds a new pins preset"

    def execute(self, context):
        wm = context.window_manager
        new_preset = wm.pins_presets.add()
        new_preset.name = "New Preset"
        new_preset.id = "%s%i" % (str(time()).replace('.',''), randint(0, 1000))
        wm.pins_presets_active_index = len(wm.pins_presets) - 1
        save_pins(context)
        return {'FINISHED'}

class VIEW3D_OT_pins_preset_remove(bpy.types.Operator):
    bl_idname = "view3d.pins_preset_remove"
    bl_label = "Remove preset"
    bl_description = "Removes an existing pins preset"

    def execute(self, context):
        wm = context.window_manager
        if not len(wm.pins_presets):
            return {'CANCELLED'}
            
        for i, pin in reversed(list(enumerate(wm.pins_data))):
            if pin.preset == active_preset_id(context):
                wm.pins_data.remove(i)
        
        wm.pins_presets.remove(wm.pins_presets_active_index)
        if wm.pins_presets_active_index >= len(wm.pins_presets):
            wm.pins_presets_active_index = len(wm.pins_presets) - 1
        save_pins(context)
        return {'FINISHED'}
        
class PINS_UL_presets(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon_value=icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label("", icon_value=icon)

class VIEW3D_PT_pins_presets(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_pins_presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Pins"
    
    bl_label = "Presets"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        row = layout.row()
        row.template_list("PINS_UL_presets", "", wm, "pins_presets", wm, "pins_presets_active_index")
        col = row.column(align=True)
        col.operator(VIEW3D_OT_pins_preset_add.bl_idname, text="", icon="ZOOMIN")
        col.operator(VIEW3D_OT_pins_preset_remove.bl_idname, text="", icon="ZOOMOUT")
        if wm.pins_presets_active_index >= 0 and wm.pins_presets_active_index < len(wm.pins_presets):
            col.separator()
            col.operator(VIEW3D_OT_pins_preset_hotkey.bl_idname, text="", icon="LINK").id = wm.pins_presets_active_index

class VIEW3D_OT_pins_preset_hotkey(bpy.types.Operator):
    bl_idname = "view3d.pins_preset_hotkey"
    bl_label = "Preset Hotkey"
    bl_description = "Preset Hotkey (Right-click this button and add shortcut)"

    id = IntProperty("Preset Index", default=0)
    
    def execute(self, context):
        wm = context.window_manager
        if self.id < 0 or self.id >= len(wm.pins_presets):
            return {'CANCELLED'}
        
        if not wm.pins_enabled:
            bpy.ops.view3d.pins('INVOKE_DEFAULT')
        
        wm.pins_presets_active_index = self.id
        return {'FINISHED'}
        
class PinsPresetItem(bpy.types.PropertyGroup):
    name = StringProperty(name="Preset name", default="Unknown")
    id = StringProperty(name="Preset id", default="0")

class PinsItem(bpy.types.PropertyGroup):
    id = StringProperty(name="Pin id", default="0")
    preset = StringProperty(name="Preset id", default="0")
    text = StringProperty(name="Pin text", default="Pin")
    mode = StringProperty(name="Pin context mode", default="")
    type = IntProperty(name="Pin type", default=0)
    call = StringProperty(name="Pin menu id", default="")
    x = FloatProperty(name="Position X", default=0.0)
    y = FloatProperty(name="Position Y", default=0.0)
    set = BoolProperty(name="Pin set", default=False)
    parent = StringProperty(name="Parent pin id", default="0")
    align = IntProperty(name="Alignment to parent", default=0)
    failed = BoolProperty(name="Execution failed", default=False)
    
class VIEW3D_OT_pins_remove_operator(bpy.types.Operator):
    bl_idname = "view3d.pins_remove_operator"
    bl_label = "Remove operator pin"
    bl_description = "Removes existing operator pin"

    id = IntProperty("Pin Index", default=0)
    
    def execute(self, context):
        wm = context.window_manager
        for pin in wm.pins_data:
            if pin.parent == wm.pins_data[self.id].id:
                pin.parent = "0"
        wm.pins_data.remove(self.id)
        save_pins(context)
        return {'FINISHED'}

class PINS_UL_pins(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        """if item.preset != active_preset_id(context):
            return"""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if item.preset == active_preset_id(context):
                layout.prop(item, "text", text="", emboss=False, icon_value=icon)
            else:
                layout.enabled = False
                layout.label(item.text + 'XX!')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label("", icon_value=icon)
        
class VIEW3D_PT_pins_remove(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_pins_remove"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Pins"
    
    bl_label = "Remove"
    
    @classmethod
    def poll(cls, context):
        return (context.window_manager.pins_presets_active_index != -1 and len(context.window_manager.pins_presets))
    
    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        col = layout.column()
        sub = col.column(align=True)
        
        #row = layout.row()
        #row.template_list("PINS_UL_pins", "", wm, "pins_data", wm, "pins_data_active_index")

        count = 0
        for i, pin in enumerate(wm.pins_data):
            if pin.preset == active_preset_id(context):
                count += 1
                if pin.type == 0:
                    sub.operator(VIEW3D_OT_pins_toggle_menu.bl_idname, text=pin.text, icon='X').menu = pin.call
                else:
                    sub.operator(VIEW3D_OT_pins_remove_operator.bl_idname, text=pin.text, icon='X').id = i
        if not count:
            sub.label("This preset has no pins.")
        
                    
def menu_pin_id(context, menu):
    for i, pin in enumerate(context.window_manager.pins_data):
        if pin.preset == active_preset_id(context):
            if pin.call == menu:
                return i
    return -1
    
class VIEW3D_OT_pins_toggle_menu(bpy.types.Operator):
    bl_idname = "view3d.pins_toggle_menu"
    bl_label = "Toggle Menu Pin"
    bl_description = "Toggle a menu pin on 3D View on or off"

    menu = StringProperty('Menu ID', default='INFO_MT_mesh_add')
    
    def execute(self, context):
        if not context.window_manager.pins_enabled:
            bpy.ops.view3d.pins('INVOKE_DEFAULT')
        
        wm = context.window_manager
        
        if not len(wm.pins_presets):
            bpy.ops.view3d.pins_preset_add('INVOKE_DEFAULT')
        
        id = menu_pin_id(context, self.menu)
        if id == -1:
            new_pin = wm.pins_data.add()
            new_pin.id = "%s%i" % (str(time()).replace('.',''), randint(0, 1000))
            new_pin.text = getattr(bpy.types, self.menu).bl_label
            new_pin.type = 0
            new_pin.call = self.menu
            new_pin.mode = context.mode
            new_pin.preset = active_preset_id(context)
        else:
            for pin in wm.pins_data:
                if pin.parent == wm.pins_data[id].id:
                    pin.parent = "0"
            wm.pins_data.remove(id)
        save_pins(context)
        return {'FINISHED'}
        
def create_properties():
    bpy.types.WindowManager.pins_presets = CollectionProperty("Pin presets", type=PinsPresetItem)
    bpy.types.WindowManager.pins_presets_active_index = IntProperty("Pin active preset index", default=0)
    bpy.types.WindowManager.pins_data = CollectionProperty("Pins", type=PinsItem)
    bpy.types.WindowManager.pins_data_active_index = IntProperty("Active pin index", default=0)
    bpy.types.WindowManager.pins_enabled = BoolProperty('Pins enabled', default=False)
    bpy.types.WindowManager.pins_invoke = BoolProperty('Pins invoke', default=False)
    bpy.types.WindowManager.pins_opacity = FloatProperty(name = 'Pins opacity', min = 0.1, max = 1.0, default = 0.65)
    bpy.types.WindowManager.pins_text = StringProperty('Pin text', default="", description="Name of your new pin. (Leave it blank for automatic naming)")
    bpy.types.WindowManager.pins_with_pars = BoolProperty('Pin with property', default=True, description="Disabled: Take new user input. Enabled: Use exact values from last use.")
    bpy.types.WindowManager.pins_loaded = BoolProperty('Pins loaded', default=False)
    
def destroy_properties():
    properties = (
        'pins_presets',
        'pins_presets_active_index',
        'pins_data',
        'pins_data_active_index',
        'pins_enabled',
        'pins_invoke',
        'pins_opacity',
        'pins_text',
        'pins_with_pars',
        'pins_loaded'
    )
    wm = bpy.context.window_manager
    for p in properties:
        if p in wm:
            del wm[p]

def pin_layout(self, context):
    self.layout.separator()
    self.layout.operator(VIEW3D_OT_pins_toggle_menu.bl_idname, icon='UNPINNED').menu = self.bl_idname
        
def inject_menu_pins():
    for type in dir(bpy.types):
        if 'INFO_MT' in type or 'VIEW3D_MT' in type:
            attr = getattr(bpy.types, type)
            if hasattr(attr, 'draw'):
                attr.append(pin_layout)

def eject_menu_pins():
    for type in dir(bpy.types):
        if 'INFO_MT' in type or 'VIEW3D_MT' in type:
            attr = getattr(bpy.types, type)
            if hasattr(attr, 'draw'):
                attr.remove(pin_layout)

def view3d_draw_callback(self, context):
    if context.window_manager.pins_invoke:
        bpy.ops.view3d.pins('INVOKE_DEFAULT')
        context.window_manager.pins_invoke = False
                
@persistent
def pins_load_handler(nothing):
    if not bpy.context.window_manager.pins_loaded:
        load_pins(bpy.context)
       
def register():
    bpy.utils.register_module(__name__)
    create_properties()
    inject_menu_pins()
    load_pins(bpy.context)
    bpy.app.handlers.load_post.append(pins_load_handler)
    print(type(bpy.types.SpaceView3D.draw_handler_add(view3d_draw_callback, (None, bpy.context), 'WINDOW', 'POST_PIXEL')))
    
def unregister():
    #Need to find a proper way to remove this later. Not really important, its removed after blender restarts anyway.
    #bpy.types.SpaceView3D.draw_handler_remove(_)
    VIEW3D_OT_pins.handle_remove(bpy.context)
    bpy.app.handlers.load_post.remove(pins_load_handler)
    bpy.utils.unregister_module(__name__)
    eject_menu_pins()
    destroy_properties()
    
if __name__ == "__main__":
    register()