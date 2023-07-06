#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Copyright (C) 2023  Kaio


from ctypes import CFUNCTYPE, POINTER, addressof, cast, byref, Structure, \
    Union, c_bool, c_byte, c_char, c_char_p, c_double, c_float, c_int,    \
    c_short, c_ubyte, c_uint, c_void_p, Array

from . import defs
from .defs import area_to_enum, region_to_enum

import bpy

version = bpy.app.version

_art_cache = {}

def factory(func):
    return func()


@factory
def event_type_to_string():
    return {
    e.value: e.identifier for e in bpy.types.Event.bl_rna.properties["type"].enum_items
}.__getitem__


def check_version_cycle():
    if bpy.app.version_cycle == "beta":
        import warnings
        warnings.warn("btypes: Beta versions of Blender not supported.")


def iter_links(link):
    for name in ("next", "prev"):
        tmp = link
        while tmp:
            contents = tmp.contents
            yield contents
            tmp = getattr(contents, name)


def get_space_type(space: str):
    area = bpy.context.window_manager.windows[0].screen.areas[0]
    enum = area_to_enum(space)

    for st in iter_links(ScrArea(area).type):
        if st.spaceid == enum:
            return st
    raise Exception(f"'{space}' does not exist")


def get_area_region_type(space: str, region: str):
    if (space, region) not in _art_cache:
        enum = region_to_enum(region)
        for art in get_space_type(space).regiontypes:
            if art.regionid == enum:
                _art_cache[space, region] = art
                break
        else:
            raise Exception(f"No '{region}' exists for '{space}'")
    return _art_cache[space, region]


class StructBase(Structure):
    """For Blender structs.

    1. Fields are defined using annotation
    2. Fields not yet defined must be wrapped in alambda.
    3. Fields referencing the containing structure must be wrapped in a lambda.
    4. initialize must be called before instances can be used.
    """
    __annotations__ = {}
    _structs = []

    def __init_subclass__(cls):
        cls._structs.append(cls)

    def __new__(cls, srna: bpy.types.bpy_struct = None):
        """When passing no arguments, creates an instance.
        
        When passing a StructRNA instance, instantiate the struct using the
        address provided by the StructRNA's as_pointer() method.
        """
        if srna is None:
            return super().__new__(cls)
        try:
            return cls.from_address(srna.as_pointer())
        except AttributeError:
            raise Exception("Not a StructRNA instance")

    def __init__(self, *_): pass  # Required

    @classmethod
    def get_member_type(cls, member: str):
        """Return the ctype of a member field."""
        try:
            return dict(cls._fields_)[member]
        except:
            raise AttributeError(f"{cls} has no member '{member}'")



class ListBase(Structure):
    """Generic linked list used throughout Blender.

    A typed ListBase class is defined using the syntax:
        ListBase(c_type)
    """
    _fields_ = (("first", c_void_p),
                ("last",  c_void_p))
    _cache = {}

    def __new__(cls, c_type=None):
        if c_type in cls._cache:
            return cls._cache[c_type]

        elif c_type is None:
            ListBase = cls

        else:
            class ListBase(Structure):
                __name__ = __qualname__ = f"ListBase{cls.__qualname__}"
                _fields_ = (("first", POINTER(c_type)),
                            ("last",  POINTER(c_type)))
                __iter__    = cls.__iter__
                __bool__    = cls.__bool__
                __getitem__ = cls.__getitem__
        return cls._cache.setdefault(c_type, ListBase)

    def __iter__(self):
        links_p = []
        # Some only have "last" member assigned, use it as a fallback.
        elem_n = self.first or self.last
        elem_p = elem_n and elem_n.contents.prev

        # Temporarily store reversed links and yield them in the right order.
        if elem_p:
            while elem_p:
                links_p.append(elem_p.contents)
                elem_p = elem_p.contents.prev
            yield from reversed(links_p)

        while elem_n:
            yield elem_n.contents
            elem_n = elem_n.contents.next

    def __getitem__(self, i):
        return list(self)[i]

    def __bool__(self):
        return bool(self.first or self.last)


def initialize():
    """Initialize StructBase subclasses, converting annotations to fields.

    This must be called
    - after all StructBase subclasses have been defined
    - before member offsets are read for address calculations
    - before the structures are used
    """

    # Beta versions aren't supported because they may have changes in DNA
    # not present in release builds. Supporting betas would be a significant
    # maintenance upkeep.
    check_version_cycle()

    is_func = type(lambda: None).__instancecheck__
    for struct in StructBase._structs:
        anons  = []
        fields = []
        for key, value in struct.__annotations__.items():
            # Lambdas
            if is_func(value):
                value = value()

            elif isinstance(value, Union):
                anons.append(key)

            fields.append((key, value))

        if anons:
            struct._anonynous_ = anons

        if fields:
            struct._fields_ = fields

    StructBase._structs.clear()
    ListBase._cache.clear()


class vec2Base(StructBase):
    """Base for vec2i, vec2s, vec2f."""
    def __setitem__(self, i, val):
        setattr(self, ("x", "y")[i], val)

    # Allow subscript, but avoid for performance reasons
    def __getitem__(self, i):
        return getattr(self, ("x", "y")[i])

    def __iter__(self):
        return iter((self.x, self.y))


class vec2i(vec2Base):
    x: c_int
    y: c_int


class vec2s(vec2Base):
    x: c_short
    y: c_short


class vec2f(vec2Base):
    x: c_float
    y: c_float


class rectBase(StructBase):
    """Base for rcti, rctf"""
    def get_position(self):
        return self.xmin, self.ymin

    def set_position(self, x, y):
        self.xmax -= self.xmin - x
        self.ymax -= self.ymin - y
        self.xmin = x
        self.ymin = y

    def __contains__(self, pt):
        x, y = pt
        return self.xmin <= x and self.xmax >= x and \
               self.ymin <= y and self.ymax >= y


# source/blender/makesdna/DNA_vec_types.h | rev 350
class rctf(rectBase):
    xmin:   c_float
    xmax:   c_float
    ymin:   c_float
    ymax:   c_float


# source/blender/makesdna/DNA_vec_types.h | rev 350
class rcti(rectBase):
    xmin:   c_int
    xmax:   c_int
    ymin:   c_int
    ymax:   c_int


# source/blender/makesdna/DNA_screen_types.h | rev 350
class Panel_Runtime(StructBase):
    region_ofsx:            c_int
    _pad4:                  c_char * 4

    if version > (2, 83):
        custom_data_ptr:    lambda: POINTER(PointerRNA)
        block:              lambda: POINTER(uiBlock)

    if version < (3, 1):
        context:            c_void_p  # bContextStore


# source/blender/makesrna/RNA_types.h | rev 350
class PointerRNA(StructBase):
    owner_id:               lambda: POINTER(ID)
    type:                   c_void_p  # StructRNA
    data:                   c_void_p


# source/blender/editors/include/UI_interface.h | rev 350
class uiBlockInteraction_CallbackData(StructBase):
    begin_fn:               c_void_p  # uiBlockInteractionBeginFn
    end_fn:                 c_void_p  # uiBlockInteractionEndFn
    update_fn:              c_void_p  # uiBlockInteractionUpdateFn
    arg1:                   c_void_p


# source/blender/editors/interface/interface_intern.hh | rev 350
class uiPopupBlockCreate(StructBase):
    create_func:            c_void_p  # uiBlockCreateFunc
    handle_create_func:     c_void_p  # uiBlockHandleCreateFunc
    arg:                    c_void_p
    arg_free:               c_void_p
    event_xy:               vec2i
    butregion:              lambda: POINTER(ARegion)
    but:                    lambda: POINTER(uiBut)


# source/blender/editors/interface/interface_intern.hh | rev 350
class uiKeyNavLock(StructBase):
    is_keynav:              c_bool
    event_xy:               vec2i


# source/blender/blenlib/BLI_vector.hh | rev 350
class blenderVector(StructBase):
    begin_:             c_void_p
    end_:               c_void_p
    capacity_end_:      c_void_p


# source/blender/editors/interface/interface_intern.hh | rev 350
class uiBlock(StructBase):
    next:                   lambda: POINTER(uiBlock)
    prev:                   lambda: POINTER(uiBlock)

    buttons:                lambda: ListBase(uiBut)
    panel:                  c_void_p  # Panel
    oldblock:               lambda: POINTER(uiBlock)

    butstore:               ListBase

    if version >= (3, 3, 2):
        button_groups:      lambda: blenderVector

    elif version > (2, 82):
        button_groups:      ListBase

    layouts:                ListBase
    curlayout:              c_void_p  # uiLayout
    contexts:               ListBase
    
    if version > (2, 93):
        views:              ListBase

    if version > (3, 3, 1):
        dynamic_listeners:  ListBase

    name:                   c_char * 128  # UI_MAX_NAME_STR
    winmat:                 c_float * 4 * 4
    rect:                   rctf
    aspect:                 c_float
    puphash:                c_uint

    func:                   c_void_p  # uiButHandleFunc
    func_arg1:              c_void_p
    func_arg2:              c_void_p
    funcN:                  c_void_p  # uiButHandleNFunc
    func_argN:              c_void_p
    butm_func:              c_void_p  # uiMenuHandleFunc
    butm_func_arg:          c_void_p
    handle_func:            c_void_p  # uiBlockHandleFunc
    handle_func_arg:        c_void_p

    if version > (2, 93):
        custom_interaction_callbacks: uiBlockInteraction_CallbackData

    block_event_func:   POINTER(c_int)
    drawextra:          c_void_p
    drawextra_arg1:     c_void_p
    drawextra_arg2:     c_void_p

    flag:               c_int
    alignnr:            c_short
    content_hints:      c_short
    direction:          c_char
    theme_style:        c_char
    emboss:             c_int
    auto_open:          c_bool
    _pad5:              c_char * 5
    auto_open_last:     c_double
    lockstr:            c_char_p
    lock:               c_bool
    active:             c_bool
    tooltipdisabled:    c_bool
    endblock:           c_bool
    bounds_type:        c_int
    bounds_offset:      c_int * 2
    bounds:             c_int
    minbounds:          c_int
    safety:             rctf
    saferct:            ListBase  # uiSafetyRct
    handle:             c_void_p  # uiPopupBlockHandle
    # ... (cont)


# source/blender/editors/interface/interface_intern.hh | rev 350
class uiBut(StructBase):
    next:               lambda: POINTER(uiBut)
    prev:               lambda: POINTER(uiBut)

    if version > (2, 90):
        layout:         c_void_p  # uiLayout

    flag:           c_int
    drawflag:       c_int
    type:           c_int
    pointype:       c_int

    bit:            c_short
    bitnr:          c_short
    retval:         c_short
    strwidth:       c_short
    alignnr:        c_short

    ofs:            c_short
    pos:            c_short
    selsta:         c_short
    selend:         c_short

    str:            c_char_p
    strdata:        c_char * 128
    drawstr:        c_char * 400

    rect:           rctf
    poin:           c_char_p

    hardmin:        c_float
    hardmax:        c_float
    softmin:        c_float
    softmax:        c_float

    a1:             c_float
    a2:             c_float
    col:            c_ubyte * 4

    if version > (3, 1):
        identity_cmp_func: c_void_p

    func:           c_void_p
    func_arg1:      c_void_p
    func_arg2:      c_void_p

    funcN:          c_void_p

    if version > (2, 82):
        func_argN:      c_void_p

    context:            c_void_p
    autocomplete_func:  c_void_p
    autofunc_arg:       c_void_p

    if version < (2, 83):
        search_create_func:     c_void_p
        search_func:            c_void_p
        free_search_arg:        c_bool
        search_arg:             c_void_p

    rename_func:        c_void_p
    rename_arg1:        c_void_p
    rename_orig:        c_void_p
    hold_func:          c_void_p
    hold_argN:          c_void_p

    tip:                c_char_p
    tip_func:           c_void_p
    tip_arg:           c_void_p

    if version > (2, 93):
        tip_arg_free: c_void_p

    disabled_info:      c_char_p

    icon:               c_int

    if version < (2, 93):
        emboss:             c_char
    else:
        emboss:             c_int
    
    if version < (3, 2):
        pie_dir:            c_byte
    else:
        pie_dir:            c_int

    changed:            c_bool
    unit_type:          c_ubyte

    if version < (3, 3):
        modifier_key:       c_short

    iconadd:            c_short

    block_create_func:  c_void_p
    menu_create_func:   c_void_p
    menu_step_func:     c_void_p

    rnapoin:            PointerRNA
    rnaprop:            c_void_p  # PropertyRNA
    rnaindex:           c_int

    if version < (2, 93):
        rnaserachpoin:  c_void_p * 3
        rnasearchprop:  c_void_p

    optype:             lambda: POINTER(wmOperatorType)
    opptr:              lambda: POINTER(PointerRNA)
    opcontext:          c_int  # enum wmOperatorCallContext
    menu_key:           c_ubyte
    extra_op_icons:     ListBase
    dragtype:           c_char
    dragflag:           c_short
    dragpoin:           c_void_p
    imb:                c_void_p
    imb_scale:          c_float
    active:             c_void_p  # uiHandleButtonData
    custom_data:        c_void_p
    editstr:            c_char_p
    editval:            POINTER(c_double)
    editvec:            POINTER(c_float)

    if version < (2, 93):
        editcoba: c_void_p
        editcumap: c_void_p
        editprofile: c_void_p

    pushed_state_func:  c_void_p
    pushed_state_arg:   c_void_p

    if version > (3, 3):
        class IconTextOverlay(StructBase):
            text: c_char * 5

        icon_overlay_text: IconTextOverlay
        _pad0: c_char * 3

    block:              lambda: POINTER(uiBlock)


# source/blender/editors/space_text/text_draw.c | rev 350
class DrawCache(StructBase):
    line_height:        POINTER(c_int)
    total_lines:        c_int
    nlines:             c_int

    winx:               c_int
    wordwrap:           c_int
    showlnum:           c_int
    tabnumber:          c_int

    lheight:            c_short
    cwidth_px:          c_char
    text_id:            c_char * 66  # MAX_ID_NAME

    update_flag:        c_short
    valid_head:         c_int
    valid_tail:         c_int


# source/blender/makesdna/DNA_ID.h | rev 350
class ID_Runtime_Remap(StructBase):
    status:                 c_int
    skipped_refcounted:     c_int
    skipped_direct:         c_int
    skipped_indirect:       c_int


# source/blender/makesdna/DNA_ID.h | rev 350
class ID_Runtime(StructBase):
    remap:                  ID_Runtime_Remap


# source/blender/makesdna/DNA_ID.h | rev 350
class ID(StructBase):
    next:                   c_void_p
    prev:                   c_void_p

    newid:                  lambda: POINTER(ID)
    lib:                    c_void_p  # Library

    if version > (2, 91):
        asset_data:         c_void_p  # AssetMetaData

    name:                   c_char * 66
    flag:                   c_short
    tag:                    c_int
    us:                     c_int
    icon_id:                c_int
    recalc:                 c_uint
    recalc_up_to_undo_push: c_uint
    recalc_after_undo_push: c_uint

    session_uuid:           c_uint
    properties:             c_void_p  # IDProperty
    override_library:       c_void_p  # IDOverrideLibrary
    orig_id:                lambda: POINTER(ID)

    py_instance:            c_void_p

    if version > (2, 93):
        library_weak_reference: c_void_p

    elif version > (2, 83):
        _pad1:              c_void_p

    if version > (3, 1):
        runtime:            ID_Runtime


# source/blender/makesdna/DNA_space_types.h | rev 350
class SpaceText_Runtime(StructBase):
    # Confusingly not line height in pixels. Use property instead.
    _lheight_px:             c_int

    cwidth_px:              c_int
    scroll_region_handle:   rcti
    scroll_region_select:   rcti
    lnum:                   c_int
    viewlines:              c_int
    scroll_px_per_line:     c_float
    _offs_px:               vec2i
    _pad1:                  c_char * 4
    drawcache:              lambda: POINTER(DrawCache)

    @property
    def lpad_px(self):
        return self.cwidth_px * (self.lnum + 3)

    @property
    def lheight_px(self):
        return int(self._lheight_px * 1.3)


# source/blender/makesdna/DNA_text_types.h | rev 350
class TextLine(StructBase):
    next:       lambda: POINTER(TextLine)
    prev:       lambda: POINTER(TextLine)

    line:       c_char_p
    format:     c_char_p
    len:        c_int
    _pad0:      c_char * 4


# source/blender/makesdna/DNA_text_types.h | rev 350
class Text(StructBase):
    id:         lambda: ID
    filepath:   c_char_p
    compiled:   c_void_p
    flags:      c_int
    
    if version < (2, 90):
        nlines: c_int
    else:
        _pad0:  c_char * 4

    lines:      ListBase(TextLine)
    curl:       POINTER(TextLine)
    sell:       POINTER(TextLine)
    curc:       c_int
    selc:       c_int
    mtime:      c_double


# source/blender/editors/interface/interface_region_menu_popup.cc | rev 350
class uiPopupMenu(StructBase):
    block:              lambda: POINTER(uiBlock)
    layout:             c_void_p  # uiLayout
    but:                lambda: POINTER(uiBut)
    butregion:          lambda: POINTER(ARegion)

    if version > (3, 3, 1):
        title:          c_char_p

    mxy:                vec2i
    popup:              c_bool
    slideout:           c_bool

    # NOTE: In 3.3.2 and up, "menu_func" is a std::function wrapper.
    menu_func:          c_void_p
    menu_arg:           c_void_p


# source/blender/makesdna/DNA_view2d_types.h | rev 350
class View2D(StructBase):
    tot:        rctf
    cur:        rctf
    vert:       rcti
    hor:        rcti
    mask:       rcti

    min:        vec2f
    max:        vec2f

    minzoom:    c_float
    maxzoom:    c_float

    scroll:     c_short
    scroll_ui:  c_short
    keeptot:    c_short
    keepzoom:   c_short
    keepofs:    c_short

    flag:       c_short
    align:      c_short

    win:        vec2s
    oldwin:     vec2s

    around:     c_short

    if version < (2, 91):
        tab_offset: POINTER(c_float)
        tab_num:    c_int
        tab_cur:    c_int

    alpha_vert: c_char
    alpha_hor:  c_char

    if version > (2, 92):
        _pad6 = c_char * 6

    sms:            c_void_p  # SmoothView2DStore
    smooth_timer:   c_void_p  # wmTimer


# source/blender/windowmanager/WM_types.h | rev 350
class wmEvent(StructBase):
    next:               lambda: POINTER(wmEvent)
    prev:               lambda: POINTER(wmEvent)

    type:               c_short
    val:                c_short

    if version < (3, 2):
        posx:           c_short
        posy:           c_short
        mvalx:          c_short
        mvaly:          c_short
    else:
        posx:           c_int
        posy:           c_int
        mvalx:          c_int
        mvaly:          c_int

    utf8_buf:           c_char * 6

    if version < (3, 2, 2):
        ascii:              c_char

    modifier:           c_char

    @property
    def ctrl(self) -> bool:
        return bool(int.from_bytes(self.modifier, "little") & 2)

    @property
    def shift(self) -> bool:
        return bool(int.from_bytes(self.modifier, "little") & 1)
    
    @property
    def alt(self) -> bool:
        return bool(int.from_bytes(self.modifier, "little") & 4)

    @property
    def type_string(self):
        return event_type_to_string(self.type)

    # XXX layout commit history is a complete mess. DO NOT USE BELOW.
    # is_repeat:          c_char
    # prevtype:           c_short
    # prevval:            c_short

    # if version < (2, 93):
    #     prev_xy:           vec2i

    # prevclicktime:      c_double
    # prevclick:          vec2i

    # if version > (2, 83):
    #     prev_xy:           vec2i

    # else:
    #     check_click:    c_char
    #     check_drag:     c_char

    # tablet:             wmTabletData
    # custom:             c_short
    # customdatafree:     c_short
    # pad2:               c_int
    # customdata:         c_void_p

    # if version > (2, 83):
    #     is_direction_inverted: c_char


# source/blender/windowmanager/wm_event_system.h | rev 350
class wmEventHandler(StructBase):  # Generic
    next:   lambda: POINTER(wmEventHandler)
    prev:   lambda: POINTER(wmEventHandler)

    type:   c_int       # enum eWM_EventHandlerType
    flag:   c_char      # enum eWM_EventHandlerFlag
    poll:   c_void_p    # func EventHandlerPoll


# source/blender/blenkernel/BKE_context.h | rev 350
class bContextPollMsgDyn_Params(StructBase):
    get_fn:         c_void_p
    free_fn:        c_void_p
    user_data:      c_void_p


# makesdna\DNA_screen_types.h
class bScreen(StructBase):
    id:                     lambda: ID
    vertbase:               ListBase
    edgebase:               ListBase
    areabase:               ListBase
    regionbase:             lambda: ListBase(ARegion)
    scene:                  c_void_p  # Scene, DNA_DEPRECATED
    flag:                   c_short
    winid:                  c_short
    redraws_flag:           c_short
    temp:                   c_char
    state:                  c_char
    do_draw:                c_char
    do_refresh:             c_char
    do_draw_gesture:        c_char
    do_draw_paintcursor:    c_char
    do_draw_drag:           c_char
    skip_handling:          c_char
    scrubbing:              c_char
    _pad1:                  c_char * 1
    active_region:          lambda: POINTER(ARegion)
    animtimer:              c_void_p  # wmTimer
    context:                c_void_p
    tooltip:                c_void_p  # wmTooltipState
    preview:                c_void_p  # PreviewImage


# source/blender/blenkernel/intern/context.cc | rev 350
class bContext(StructBase):
    thread:         c_int

    class _wm(StructBase):
        manager:        lambda: POINTER(wmWindowManager)
        window:         lambda: POINTER(wmWindow)
        workspace:      c_void_p  # WorkSpace
        screen:         c_void_p  # bScreen
        area:           lambda: POINTER(ScrArea)
        region:         lambda: POINTER(ARegion)
        menu:           lambda: POINTER(ARegion)
        gizmo_group:    c_void_p  # wmGizmoGroup
        store:          c_void_p  # bContextStore

        operator_poll_msg: c_char_p
        operator_poll_msg_dyn_params: bContextPollMsgDyn_Params

    wm: _wm
    del _wm

    class _data(StructBase):
        main:               c_void_p  # Main
        scene:              c_void_p  # Scene
        recursion:          c_int
        py_init:            c_bool
        py_context:         c_void_p
        py_context_orig:    c_void_p
    
    data: _data
    del _data


# source/blender/makesdna/DNA_windowmanager_types.h | rev 350
class wmOperator(StructBase):
    next:           lambda: POINTER(wmOperator)
    prev:           lambda: POINTER(wmOperator)

    idname:         c_char * 64
    properties:     c_void_p  # IDProperty
    type:           lambda: POINTER(wmOperatorType)
    customdata:     c_void_p
    pyinstance:     c_void_p
    ptr:            lambda: POINTER(PointerRNA)
    reports:        c_void_p  # ReportList
    macro:          ListBase
    opm:            lambda: POINTER(wmOperator)
    layout:         c_void_p  # uiLayout
    flag:           c_short
    _pad6:          c_char * 6


# source/blender/windowmanager/WM_types.h | rev 350
class wmOperatorType(StructBase):
    name:                   c_char_p
    idname:                 c_char_p
    translation_context:    c_char_p
    description:            c_char_p
    undo_group:             c_char_p

    exec:                   CFUNCTYPE(c_int, POINTER(bContext), POINTER(wmOperator))
    check:                  POINTER(c_bool)
    invoke:                 CFUNCTYPE(c_int, POINTER(bContext), POINTER(wmOperator), POINTER(wmEvent))
    cancel:                 CFUNCTYPE(None, POINTER(bContext), POINTER(wmOperator))
    modal:                  CFUNCTYPE(c_int, POINTER(bContext), POINTER(wmOperator), POINTER(wmEvent))
    poll:                   CFUNCTYPE(c_bool, POINTER(bContext))
    poll_property:          CFUNCTYPE(c_bool, POINTER(bContext), POINTER(wmOperator), c_void_p)  # PropertyRNA
    ui:                     CFUNCTYPE(None, POINTER(bContext), POINTER(wmOperator))
    get_name:               lambda: CFUNCTYPE(c_char_p, POINTER(wmOperatorType), POINTER(PointerRNA))
    get_description:        lambda: CFUNCTYPE(c_char_p, POINTER(bContext), POINTER(wmOperatorType), POINTER(PointerRNA))
    srna:                   c_void_p  # StructRNA

    last_properties:        c_void_p  # IDProperty
    prop:                   c_void_p  # PropertyRNA
    macro:                  ListBase  # wmOperatorTypeMacro
    modalkeymap:            c_void_p  # wmKeyMap
    pyop_poll:              lambda: CFUNCTYPE(c_bool, POINTER(bContext), POINTER(wmOperatorType))
    rna_ext:                c_void_p * 4  # ExtensionRNA

    if version > (2, 93):
        cursor_pending:     c_int

    flag:                   c_short


# source/blender/windowmanager/wm_event_system.h | rev 350
class wmEventHandler_Op(StructBase):

    head:           wmEventHandler
    op:             lambda: POINTER(wmOperator)
    is_file_select: c_bool
    
    class op_context(StructBase):
        win:            lambda: POINTER(wmWindow)
        area:           lambda: POINTER(ScrArea)
        region:         lambda: POINTER(ARegion)
        region_type:    c_short

    context:        op_context
    del op_context


# source/blender/blenkernel/BKE_screen.h | rev 350
class SpaceType(StructBase):
    next:                       lambda: POINTER(SpaceType)
    prev:                       lambda: POINTER(SpaceType)

    name:                       c_char * 64  # BKE_ST_MAXNAME
    spaceid:                    c_int
    iconid:                     c_int

    create:                     c_void_p
    free:                       lambda: CFUNCTYPE(None, c_void_p)  # SpaceLink
    init:                       c_void_p
    exit:                       c_void_p
    listener:                   c_void_p

    deactivate:                 lambda: CFUNCTYPE(None, POINTER(ScrArea))
    refresh:                    c_void_p
    duplicate:                  c_void_p

    operatortypes:              c_void_p
    keymap:                     c_void_p
    dropboxes:                  c_void_p

    gizmos:                     c_void_p
    context:                    c_void_p
    id_remap:                   c_void_p

    space_subtype_get:          c_void_p
    space_subtype_set:          c_void_p
    space_subtype_item_extend:  c_void_p

    if version > (3, 3, 0):
        blend_read_data:        c_void_p
        blend_read_lib:         c_void_p
        blend_write:            c_void_p

    regiontypes:                lambda: ListBase(ARegionType)
    keymapflag:                 c_int


# source/blender/makesdna/DNA_screen_types.h | rev 350
class ScrArea_Runtime(StructBase):
    tool:           c_void_p  # bToolRef
    is_tool_set:    c_char
    _pad0:          c_char * 7


# source/blender/blenkernel/BKE_screen.h | rev 350
class ARegionType(StructBase):
    next:                       lambda: POINTER(ARegionType)
    prev:                       lambda: POINTER(ARegionType)
    
    regionid:                   c_int
    init:                       c_void_p
    exit:                       c_void_p
    draw:                       lambda: CFUNCTYPE(None, POINTER(bContext), POINTER(ARegion))

    if version > (2, 83):
        draw_overlay:           c_void_p

    layout:                     c_void_p
    snap_size:                  c_void_p
    listener:                   lambda: CFUNCTYPE(None, c_void_p)
    message_subscribe:          c_void_p
    free:                       c_void_p
    duplicate:                  c_void_p
    operatortypes:              c_void_p
    keymap:                     c_void_p

    # Cursor handler
    cursor:                     lambda: CFUNCTYPE(None, POINTER(wmWindow), POINTER(ScrArea), POINTER(ARegion))
    context:                    c_void_p  # bContextDataCallback

    if version > (2, 83):
        on_view2d_changed:      c_void_p

    drawcalls:                  ListBase
    paneltypes:                 ListBase
    headertypes:                ListBase

    minsize:                    vec2i
    prefsize:                   vec2i
    keymapflag:                 c_int
    do_lock:                    c_short
    lock:                       c_short
    clip_gizmo_events_by_ui:    c_bool
    event_cursor:               c_short


class ARegion_Runtime(StructBase):
    category:           c_char_p

    visible_rect:       rcti

    offset_x:           c_int
    offset_y:           c_int

    block_name_map:     c_void_p  # GHash


# source/blender/makesdna/DNA_screen_types.h | rev 350
class ARegion(StructBase):
    next:                   lambda: POINTER(ARegion)
    prev:                   lambda: POINTER(ARegion)

    view2D:                 View2D
    winrct:                 rcti
    drawrct:                rcti
    winx:                   c_short
    winy:                   c_short

    visible:                c_short
    regiontype:             c_short
    alignment:              c_short
    flag:                   c_short

    sizex:                  c_short
    sizey:                  c_short

    do_draw:                c_short
    do_draw_overlay:        c_short
    overlap:                c_short
    flagfullscreen:         c_short

    type:                   lambda: POINTER(ARegionType)  # ARegionType

    uiblocks:               ListBase(uiBlock)
    panels:                 ListBase  # Panel
    panels_category_active: ListBase
    ui_lists:               ListBase
    ui_previews:            ListBase
    handlers:               ListBase(wmEventHandler)
    panels_category:        ListBase

    gizmo_map:              c_void_p  # wmGizmoMap
    regiontimer:            c_void_p  # wmTimer
    draw_buffer:            c_void_p  # wmDrawBuffer

    headerstr:              c_char_p
    regiondata:             c_void_p

    runtime:                ARegion_Runtime


# source/blender/makesdna/DNA_space_types.h | rev 350
class SpaceLink(StructBase):
    next:                   lambda: POINTER(SpaceLink)
    prev:                   lambda: POINTER(SpaceLink)

    regionbase:             ListBase(ARegion)
    spacetype:              c_char
    link_flag:              c_char
    _pad0:                  c_char * 6


# source/blender/makesdna/DNA_screen_types.h | rev 350
class ScrArea(StructBase):
    next:                   lambda: POINTER(ScrArea)
    prev:                   lambda: POINTER(ScrArea)

    v1:                     c_void_p  # ScrVert
    v2:                     c_void_p  # ScrVert
    v3:                     c_void_p  # ScrVert
    v4:                     c_void_p  # ScrVert

    full:                   c_void_p  # bScreen
    totrct:                 rcti

    spacetype:              c_char
    butspacetype:           c_char
    butspacetype_subtype:   c_short

    win:                    vec2s
    headertype:             c_char  # DNA_DEPRECATED
    do_refresh:             c_char
    flag:                   c_short

    region_active_win:      c_short
    _pad2:                  c_char * 2

    type:                   POINTER(SpaceType)
    global_:                c_void_p  # ScrGlobalAreaData
    spacedata:              ListBase(SpaceLink)  # SpaceLink
    regionbase:             ListBase(ARegion)
    handlers:               ListBase  # wmEventHandler and wmEventHandler_Op
    actionzones:            ListBase  # AZone
    runtime:                ScrArea_Runtime

    @property
    def action_zones(self):
        az = self.actionzones.first
        while az:
            yield az.contents
            az = az.contents.prev


# source/blender/makesdna/DNA_space_types.h | rev 350
class SpaceText(StructBase):
    next:               POINTER(SpaceLink)
    prev:               POINTER(SpaceLink)

    regionbase:         ListBase(ARegion)
    spacetype:          c_char
    link_flag:          c_char
    pad0:               c_char * 6

    text:               POINTER(Text)

    top:                c_int
    left:               c_int
    _pad1:              c_char * 4

    flags:              c_short

    lheight:            c_short
    tabnumber:          c_int

    wordwrap:           c_char
    doplugins:          c_char
    showlnum:           c_char
    showsyntax:         c_char
    line_hlight:        c_char
    overwrite:          c_char
    live_edit:          c_char
    _pad2:              c_char * 1

    findstr:            c_char * 256
    replacestr:         c_char * 256

    margin_column:      c_short
    _pad3:              c_char * 2
    runtime:            SpaceText_Runtime


# source/blender/makesdna/DNA_windowmanager_types.h  | rev 350
class wmWindow(StructBase):
    next:                   lambda: POINTER(wmWindow)
    prev:                   lambda: POINTER(wmWindow)

    ghostwin:               c_void_p
    gpuctx:                 c_void_p

    parent:                 lambda: POINTER(wmWindow)

    scene:                  c_void_p
    new_scene:              c_void_p
    view_layer_name:        c_char * 64

    if version >= (3, 3):
        unpinned_scene:     c_void_p  # Scene

    workspace_hook:         c_void_p
    global_areas:           ListBase * 3  # ScrAreaMap

    screen:                 c_void_p  # bScreen  # (deprecated)

    if version > (2, 92):
        winid:              c_int

    pos:                    c_short * 2
    size:                   c_short * 2
    windowstate:            c_char
    active:                 c_char

    if version < (3, 0):
        _pad0:              c_char * 4

    cursor:                 c_short
    lastcursor:             c_short
    modalcursor:            c_short
    grabcursor:             c_short

    if version >= (3, 5, 0):
        pie_event_type_lock: c_short
        pie_event_type_last: c_short

    addmousemove:           c_char
    tag_cursor_refresh:     c_char

    if version <= (2, 93):
        winid:                          c_int

    if version > (2, 93):
        event_queue_check_click:        c_char
        event_queue_check_drag:         c_char
        event_queue_check_drag_handled: c_char

    # TODO: Use less than. This is currently a 3.5.0 beta workaround.
    if version <= (3, 5, 0):
        _pad0:                                  c_char * 1

    else:
        event_queue_consecutive_gesture_type:   c_char
        event_queue_consecutive_gesture_xy:     c_int * 2
        event_queue_consecutive_gesture_data:   c_void_p  # wmEvent_ConsecutiveData

    if version < (3, 5, 0):
        pie_event_type_lock:    c_short
        pie_event_type_last:    c_short

    eventstate:             lambda: POINTER(wmEvent)
    
    if version > (3, 1):
        event_last_handled: lambda: POINTER(wmEvent)

    if version < (3, 2):
        tweak:                  c_void_p

    ime_data:               c_void_p  # wmIMEData
    event_queue:            ListBase
    handlers:               ListBase(wmEventHandler)
    modalhandlers:          ListBase(wmEventHandler)
    gesture:                ListBase
    stereo3d_format:        c_void_p
    drawcalls:              ListBase
    cursor_keymap_status:   c_void_p


# source/blender/makesdna/DNA_windowmanager_types.h | rev 350
class ReportList(StructBase):
    list:           ListBase  # Report
    printlevel:     c_int
    storelevel:     c_int
    flag:           c_int
    _pad4:          c_char * 4
    reporttimer:    c_void_p  # wmTimer


# source/blender/makesdna/DNA_windowmanager_types.h | rev 350
class wmWindowManager(StructBase):
    ID:                         lambda: ID

    windrawable:                lambda: POINTER(wmWindow)
    winactive:                  lambda: POINTER(wmWindow)
    windows:                    ListBase(wmWindow)

    initialized:                c_short
    file_saved:                 c_short
    op_undo_depth:              c_short
    outliner_sync_select_dirty: c_short

    operators:                  ListBase(wmOperator)  # Operator undo history

    notifier_queue:             ListBase

    if version > (3, 2, 2):
        notifier_queue_set:     c_void_p  # GSet

    reports:                    ReportList
    jobs:                       ListBase
    paintcursors:               ListBase
    drags:                      ListBase
    keyconfigs:                 ListBase

    defaultconf:                c_void_p  # wmKeyConfig
    addonconf:                  c_void_p  # wmKeyConfig
    userconf:                   c_void_p  # wmKeyConfig

    timers:                     ListBase
    autosavetimer:              c_void_p  # wmTimer
    undo_stack:                 c_void_p  # UndoStack
    is_interface_locked:        c_char
    _pad7:                      c_char * 7
    message_bus:                c_void_p  # wmMsgBus
    # ... (cont)


# source/blender/makesdna/DNA_userdef_types.h | rev 350
class SolidLight(StructBase):
    flag:       c_int
    smooth:     c_float

    if version < (3, 3, 1):
        _pad0:      c_char * 8

    col:        c_float * 4
    spec:       c_float * 4
    vec:        c_float * 4


# source/blender/makesdna/DNA_userdef_types.h | rev 350
class UserDef(StructBase):
    versionfile:            c_int
    subversionfile:         c_int

    flag:                   c_int
    dupflag:                c_uint
    pref_flag:              c_char
    savetime:               c_char

    mouse_emulate_3_button_modifier: c_char
    _pad4:                  c_char * 1

    tempdir:                c_char * 768
    fontdir:                c_char * 768
    renderdir:              c_char * 1024
    render_cachedir:        c_char * 768
    textudir:               c_char * 768
    pythondir:              c_char * 768
    sounddir:               c_char * 768
    i18ndir:                c_char * 768
    image_editor:           c_char * 1024
    anim_player:            c_char * 1024
    anim_player_preset:     c_int

    v2d_min_gridsize:       c_short
    timecode_style:         c_short
    versions:               c_short
    dbl_click_time:         c_short

    if version > (2, 83):
        _pad0:              c_char * 3

    if version < (2, 84):
        _pad0:              c_char * 2
        wheellinescroll:    c_char

    mini_axis_type:         c_char
    uiflag:                 c_int
    uiflag2:                c_char
    gpu_flag:               c_char
    _pad8:                  c_char * 6
    app_flag:               c_char
    viewzoom:               c_char
    language:               c_short

    mixbufsize:             c_int
    audiodevice:            c_int
    audiorate:              c_int
    audioformat:            c_int
    audiochannels:          c_int

    ui_scale:               c_float
    ui_line_width:          c_int
    dpi:                    c_int
    dpi_fac:                c_float
    inv_dpi_fac:            c_float
    pixelsize:              c_float
    virtual_pixel:          c_int

    scrollback:             c_int
    node_margin:            c_char
    _pad2:                  c_char * 1
    transopts:              c_short
    menuthreshold1:         c_short
    menuthreshold2:         c_short
    app_template:           c_char * 64

    themes:                 ListBase
    uifonts:                ListBase
    uistyles:               ListBase
    user_keymaps:           ListBase
    user_keyconfig_prefs:   ListBase
    addons:                 ListBase
    autoexec_paths:         ListBase
    user_menus:             ListBase

    if version > (2, 83):
        asset_libraries:    ListBase

    keyconfigstr:           c_char * 64

    if version > (3, 3, 3):
        active_asset_library: c_short

    undosteps:              c_short

    if version < (3, 3, 4):
        _pad1:                  c_char * 2

    undomemory:             c_int
    gpu_viewport_quality:   c_float  # DNA_DEPRECATED

    gp_manhattan_dist:      c_short
    gp_euclidean_dist:      c_short
    gp_eraser:              c_short
    gp_settings:            c_short

    _pad13:                 c_char * 4
    light_param:            lambda: SolidLight * 4
    light_ambient:          c_float * 3
    gizmo_flag:             c_char
    gizmo_size:             c_char

    if version > (2, 83):
        gizmo_size_navigate_v3d: c_char
        _pad3:              c_char * 5

    edit_studio_light:      c_short
    lookdev_sphere_size:    c_short
    vbotimeout:             c_short
    vbocollectrate:         c_short
    textimeout:             c_short
    texcollectrate:         c_short
    memcachelimit:          c_int
    prefetchframes:         c_int
    pad_rot_angle:          c_float
    _pad12:                 c_char * 4

    rvisize:                c_short
    rvibright:              c_short
    recent_files:           c_short
    smooth_viewtx:          c_short
    glreslimit:             c_short
    color_picker_type:      c_short
    auto_smoothing_new:     c_char
    ipo_new:                c_char
    keyhandles_new:         c_char
    _pad11:                 c_char * 4

    view_frame_type:        c_char
    view_frame_keyframes:   c_int
    view_frame_seconds:     c_float

    if version > (3, 3, 4):
        gpu_backend:        c_short
        _pad7:              c_char * 4
    
    if version < (3, 3, 5):
        _pad7:              c_char * 6

    widget_unit:            c_short
    # ... (cont)
