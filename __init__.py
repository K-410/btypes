import bpy
from ctypes import c_int, c_uint, c_short, c_bool, c_char, \
    c_char_p, c_float, c_double, c_ubyte, c_byte, c_void_p, \
    Structure, sizeof, addressof, c_uint64, POINTER, CFUNCTYPE, Union, Array


functype = type(lambda: None)
version = bpy.app.version


class StructBase(Structure):
    """For Blender structs.

    1. Fields are defined using annotation
    2. Fields that refer to the containing struct must be wrapped in lambda.
    3. Fields not yet defined must be wrapped in lambda.
    4. initialize must be called before StructBase instances can be used.
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


class ListBase(Structure):
    """Generic (void pointer) ListBase used throughout Blender.
    
    ListBase stores the first/last pointers of a linked list.

    A Typed ListBase class is created using syntax:
        ListBase(c_type)  # Returns a new class, not an instance
    """
    _fields_ = (("first", c_void_p), ("last",  c_void_p))
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

    def __getitem__(self, i): return list(self)[i]

    def __bool__(self): return bool(self.first or self.last)


def initialize():
    """Initialize StructBase subclasses, converting annotations to fields.

    This must be called after all subclasses have been defined, and before
    any of their functions are used, or offsets are read.
    """
    for struct in StructBase._structs:
        fields = []
        anons = []
        for key, value in struct.__annotations__.items():
            if isinstance(value, functype):
                value = value()
            elif isinstance(value, Union):
                anons.append(key)
            fields.append((key, value))

        if anons:
            struct._anonynous_ = anons

        # Base classes might not have _fields_. Don't set anything.
        if fields:
            struct._fields_ = fields
        struct.__annotations__.clear()

    StructBase._structs.clear()
    ListBase._cache.clear()


class vec2Base(StructBase):
    """Base for Blender's vec2 short/int/float types"""
    def __getitem__(self, i):
        return getattr(self, ("x", "y")[i])

    def __setitem__(self, i, val):
        setattr(self, ("x", "y")[i], val)

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
    """Base for Blender's rct int/float types"""
    def get_position(self):
        return self.xmin, self.ymin

    def set_position(self, x, y):
        self.xmax -= self.xmin - x
        self.ymax -= self.ymin - y
        self.xmin = x
        self.ymin = y

    def __contains__(self, pt):
        return (self.xmin, self.ymin) <= pt <= (self.xmax, self.ymax)

# source\blender\makesdna\DNA_vec_types.h
class rctf(rectBase):
    xmin:   c_float
    xmax:   c_float
    ymin:   c_float
    ymax:   c_float


# source\blender\makesdna\DNA_vec_types.h
class rcti(rectBase):
    xmin:   c_int
    xmax:   c_int
    ymin:   c_int
    ymax:   c_int


# source\blender\makesdna\DNA_screen_types.h
class Panel_Runtime(StructBase):
    region_ofsx:            c_int
    _pad4:                  c_char * 4

    if version > (2, 83):
        custom_data_ptr:    lambda: POINTER(PointerRNA)
        block:              lambda: POINTER(uiBlock)


class PointerRNA(StructBase):
    owner_id:   lambda: POINTER(ID)
    type:       lambda: POINTER(StructRNA)
    data:       c_void_p


class PropertyRNA(StructBase):
    next: lambda: POINTER(PropertyRNA)
    prev: lambda: POINTER(PropertyRNA)
    magic: c_int
    identifier: c_char_p
    flag: c_int
    flag_override: c_int
    flag_parameter: c_short
    flag_internal: c_short
    tags: c_short
    name: c_char_p
    description: c_char_p
    icon: c_int
    translation_context: c_char_p
    type: c_int


class PropertyPointerRNA(StructBase):
    ptr: PointerRNA
    prop: c_void_p
    # prop: lambda: POINTER(PropertyRNA)


# source\blender\makesdna\DNA_screen_types.h
class Panel(StructBase):
    next:           lambda: POINTER(Panel)
    prev:           lambda: POINTER(Panel)
    type:           c_void_p  # PanelType
    layout:         c_void_p  # uiLayout
    panelname:      c_char * 64
    drawname:       c_char * 64
    ofs:            vec2i
    size:           vec2i
    blocksize:      vec2i
    labelofs:       c_short

    if version < (2, 93):
        _pad4:      c_char * 4

    flag:           c_short
    runtime_flag:   c_short
    _pad6:          c_char * 6
    sortorder:      c_int
    activedata:     c_void_p
    children:       lambda: ListBase(Panel)
    runtime:        lambda: Panel_Runtime


# source/blender/editors/include/UI_interface.h (3.0)
class uiBlockInteraction_CallbackData(StructBase):
    begin_fn:   c_void_p
    end_fn:     c_void_p
    update_fn:  c_void_p
    arg1:       c_void_p


# source\blender\editors\interface\interface_intern.h
class uiPopupBlockCreate(StructBase):
    create_func:        c_void_p
    handle_create_func: c_void_p
    arg:                c_void_p
    arg_free:           c_void_p
    event_xy:           vec2i
    butregion:          lambda: POINTER(ARegion)
    but:                lambda: POINTER(uiBut)


# source\blender\editors\interface\interface_intern.h
class uiKeyNavLock(StructBase):
    is_keynav:  c_bool
    event_xy:   vec2i


# source\blender\editors\interface\interface_handlers.c
class uiSelectContextStore(StructBase):
    elems:      c_void_p  # uiSelectContextElem
    elems_len:  c_int
    do_free:    c_bool
    is_enabled: c_bool
    is_copy:    c_bool


# source\blender\editors\interface\interface_handlers.c
class uiButMultiState(StructBase):
    origvalue:      c_double
    but:            lambda: POINTER(uiBut)
    select_others:  uiSelectContextStore


# source\blender\editors\interface\interface_handlers.c
class uiHandleButtonMulti(StructBase):
    init:               c_int  # enum (See interface_handlers.c)
    has_mbuts:          c_bool
    mbuts:              c_void_p  # LinkNode
    bs_mbuts:           c_void_p  # uiButStore
    is_proportional:    c_bool
    skip:               c_bool
    drag_dir:           vec2f
    drag_start:         vec2i
    drag_lock_x:        c_int


# source\blender\editors\interface\interface_handlers.c
class uiHandleButtonData(StructBase):
    wm:                         lambda: POINTER(wmWindowManager)
    window:                     lambda: POINTER(wmWindow)
    area:                       lambda: POINTER(ScrArea)
    region:                     lambda: POINTER(ARegion)
    interactive:                c_bool
    state:                      c_int  # enum (uiHandleButtonState)
    retval:                     c_int
    cancel:                     c_bool
    escapecancel:               c_bool
    applied:                    c_bool
    applied_interactive:        c_bool
    changed_cursor:             c_bool
    flashtimer:                 lambda: POINTER(wmTimer)
    str:                        c_char_p
    origstr:                    c_char_p
    value:                      c_double
    origvalue:                  c_double
    startvalue:                 c_double
    vec:                        c_float * 3
    origvec:                    c_float * 3
    coba:                       c_void_p  # ColorBand
    tooltip_force:              c_uint
    used_mouse:                 c_bool
    autoopentimer:              lambda: POINTER(wmTimer)
    hold_action_timer:          lambda: POINTER(wmTimer)
    maxlen:                     c_int
    sel_pos_init:               c_int
    is_str_dynamic:             c_bool
    draglast:                   vec2i
    dragstart:                  vec2i
    draglastvalue:              c_int
    dragstartvalue:             c_int
    dragchange:                 c_bool
    draglock:                   c_bool
    dragsel:                    c_int
    dragf:                      c_float
    dragfstart:                 c_float
    dragcbd:                    c_void_p  # CBData
    drag_map_soft_min:          c_float
    drag_map_soft_max:          c_float
    ungrab_mval:                vec2f
    menu:                       lambda: POINTER(uiPopupBlockHandle)
    menuretval:                 c_int
    searchbox:                  lambda: POINTER(ARegion)
    searchbox_keynav_state:     uiKeyNavLock
    multi_data:                 uiHandleButtonMulti
    select_others:              uiSelectContextStore

    if version >= (2, 93):
        if version >= (3, 0):
            custom_interaction_handle:  c_void_p  # uiBlockInteraction_Handle
        undo_stack_text:                c_void_p  # uiUndoStack_Text

    custom_interaction_handle:  c_void_p  # uiBlockInteraction_Handle
    undo_stack_text:            c_void_p  # uiUndoStack_Text
    posttype:                   c_int  # enum
    postbut:                    lambda: POINTER(uiBut)


# source\blender\editors\interface\interface_intern.h
class uiPopupBlockHandle(StructBase):
    region:             lambda: POINTER(ARegion)
    towards_xy:         vec2f
    towardstime:        c_double
    dotowards:          c_bool

    popup:              c_bool
    popup_func:         c_void_p
    cancel_func:        c_void_p
    popup_arg:          c_void_p

    popup_create_vars:  lambda: uiPopupBlockCreate
    can_refresh:        c_bool
    refresh:            c_bool

    scrolltimer:        lambda: POINTER(wmTimer)
    scrolloffset:       c_float
    keynav_state:       uiKeyNavLock

    popup_op:           lambda: POINTER(wmOperator)

    if version < (2, 93):
        optype:         lambda: POINTER(wmOperatorType)

    ctx_area:           lambda: POINTER(ScrArea)
    ctx_region:         lambda: POINTER(ARegion)

    if version < (2, 93):
        opcontext:      c_int

    butretval:          c_int
    menuretval:         c_int
    retvalue:           c_int
    retvec:             c_float * 4

    direction:          c_int
    prev_block_rect:    rctf
    prev_butrct:        rctf
    prev_dir1:          c_short
    prev_dir2:          c_short
    prev_bounds_offset: vec2i
    max_size:           vec2f
    is_grab:            c_bool
    grab_xy_prev:       vec2i


# source\blender\editors\interface\interface_intern.h
class uiBlock(StructBase):
    next:               lambda: POINTER(uiBlock)
    prev:               lambda: POINTER(uiBlock)
    buttons:            lambda: ListBase(uiBut)
    panel:              lambda: POINTER(Panel)
    oldblock:           lambda: POINTER(uiBlock)
    butstore:           ListBase

    if version >= (2, 83):
        button_groups:  ListBase

    layouts:            ListBase
    curlayout:          c_void_p  # uiLayout
    contexts:           ListBase
    
    if version >= (3, 0):
        views:          ListBase

    name:               c_char * 128  # UI_MAX_NAME_STR
    winmat:             c_float * 4 * 4
    rect:               rctf
    aspect:             c_float
    puphash:            c_uint
    func:               c_void_p  # uiButHandleFunc
    func_arg1:          c_void_p
    func_arg2:          c_void_p
    funcN:              c_void_p  # uiButHandleNFunc
    func_argN:          c_void_p
    butm_func:          c_void_p  # uiMenuHandleFunc
    butm_func_arg:      c_void_p
    handle_func:        c_void_p  # uiBlockHandleFunc
    handle_func_arg:    c_void_p

    if version >= (3, 0):
        custom_interaction_callbacks: uiBlockInteraction_CallbackData

    block_event_func:   POINTER(c_int)
    drawextra:          c_void_p  # func
    drawextra_arg1:     c_void_p
    drawextra_arg2:     c_void_p
    flag:               c_int
    alignnr:            c_short
    content_hints:      c_short
    direction:          c_char
    theme_style:        c_char
    emboss:             c_int  # eUIEmbossType after (2, 92)
    # emboss:             c_char  # eUIEmbossType after (2, 92)
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
    handle:             lambda: POINTER(uiPopupBlockHandle)
    # ... (cont)


# source\blender\editors\interface\interface_intern.h
class uiBut(StructBase):
    next:               lambda: POINTER(uiBut)
    prev:               lambda: POINTER(uiBut)
    if version >= (2, 91):
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

    if version >= (3, 2):
        identity_cmp_func: c_void_p

    func:           c_void_p
    func_arg1:      c_void_p
    func_arg2:      c_void_p
    funcN:          c_void_p

    if version >= (2, 83):
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

    if version >= (3, 0):
        tip_arg_free: c_void_p  # func

    disabled_info:      c_char_p
    icon:               c_int
    emboss:             c_char  # 'dt' pre-(2, 91), 'eUIEmbossType' post-(2, 91)
    pie_dir:            c_byte
    changed:            c_bool
    unit_type:          c_ubyte

    if version < (3, 3):
        modifier_key:       c_short

    iconadd:            c_short
    block_create_func:  c_void_p
    menu_create_func:   c_void_p
    menu_step_func:     c_void_p
    rnapoin:            PointerRNA
    rnaprop:            lambda: POINTER(PropertyRNA)
    rnaindex:           c_int

    if version < (2, 93):
        rnaserachpoin:  c_void_p * 3
        rnasearchprop:  c_void_p

    optype:             lambda: POINTER(wmOperatorType)
    opptr:              lambda: POINTER(PointerRNA)
    opcontext:          c_short  # XXX c_short enum?
    menu_key:           c_ubyte
    extra_op_icons:     ListBase
    dragtype:           c_char
    dragflag:           c_short
    dragpoin:           c_void_p
    imb:                c_void_p
    imb_scale:          c_float
    active:             lambda: POINTER(uiHandleButtonData)
    custom_data:        c_void_p
    editstr:            c_char_p
    editval:            POINTER(c_double)
    editvec:            POINTER(c_float)

    if version < (2, 93):
        editcoba: c_void_p
        editcumap: c_void_p
        editprofile: c_void_p

    pushed_state_func:  POINTER(c_int)
    pushed_state_arg:   c_void_p
    block:              lambda: POINTER(uiBlock)


# source\blender\editors\space_text\text_draw.c
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


# source\blender\makesdna\DNA_windowmanager_types.h
class wmOperatorTypeMacro(StructBase):
    next:               lambda: POINTER(wmOperatorTypeMacro)
    prev:               lambda: POINTER(wmOperatorTypeMacro)
    idname:             c_char * 64
    properties:         lambda: POINTER(IDProperty)
    ptr:                lambda: POINTER(PointerRNA)


# source\blender\makesdna\DNA_ID.h
class IDPropertyData(StructBase):
    pointer:    c_void_p
    group:      ListBase
    val:        c_int
    val2:       c_int


# source\blender\makesdna\DNA_ID.h
class IDProperty(StructBase):
    next:       lambda: POINTER(IDProperty)
    prev:       lambda: POINTER(IDProperty)
    type:       c_char
    subtype:    c_char
    flag:       c_short
    name:       c_char * 64
    saved:      c_int
    data:       lambda: IDPropertyData
    len:        c_int
    totallen:   c_int

    if version >= (3, 0):
        ui_data: c_void_p  # IDPropertyUIData


if version >= (3, 2):
    # source/blender/makesdna/DNA_ID.h
    class ID_Runtime_Remap(StructBase):
        status: c_int
        skipped_refcounted: c_int
        skipped_direct: c_int
        skipped_indirect: c_int


    # source/blender/makesdna/DNA_ID.h
    class ID_Runtime(StructBase):
        remap: ID_Runtime_Remap


# source\blender\makesdna\DNA_ID.h
class ID(StructBase):
    next:               c_void_p
    prev:               c_void_p
    newid:              lambda: POINTER(ID)
    lib:                c_void_p  # Library

    if version >= (2, 92):
        asset_data:     c_void_p  # AssetMetaData

    name:               c_char * 66
    flag:               c_short
    tag:                c_int
    us:                 c_int
    icon_id:            c_int
    recalc:             c_int
    recalc_up_to_undo_push: c_int
    recalc_after_undo_push: c_int
    session_uuid:       c_uint
    properties:         lambda: POINTER(IDProperty)
    override_library:   c_void_p  # IDOverrideLibrary
    orig_id:            lambda: POINTER(ID)
    py_instance:        c_void_p

    if version >= (3, 0):
        library_weak_reference: c_void_p

    elif version > (2, 83):
        _pad1:          c_void_p

    if version >= (3, 2):
        runtime:            ID_Runtime


# source\blender\makesdna\DNA_space_types.h
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


# source\blender\makesdna\DNA_text_types.h
class TextLine(StructBase):
    next:       lambda: POINTER(TextLine)
    prev:       lambda: POINTER(TextLine)
    line:       c_char_p
    format:     c_char_p
    len:        c_int
    _pad0:      c_char * 4


# source\blender\makesdna\DNA_text_types.h
class Text(StructBase):
    id:         lambda: ID
    filepath:   c_char_p
    compiled:   c_void_p
    flags:      c_int
    
    if version <= (2, 83):
        nlines: c_int
    else:
        _pad0:  c_char * 4

    lines:      ListBase(TextLine)
    curl:       POINTER(TextLine)
    sell:       POINTER(TextLine)
    curc:       c_int
    selc:       c_int
    mtime:      c_double


# source\blender\editors\interface\interface_region_menu_popup.c
class uiPopupMenu(StructBase):
    block:      lambda: POINTER(uiBlock)
    layout:     c_void_p  # uiLayout
    but:        lambda: POINTER(uiBut)
    butregion:  lambda: POINTER(ARegion)
    mxy:        vec2i
    popup:      c_bool
    slideout:   c_bool
    menu_func:  c_void_p
    menu_arg:   c_void_p


# source\blender\makesdna\DNA_view2d_types.h
class View2D(StructBase):
    tot:        rctf
    # Current viewing rectangle
    cur:        rctf
    vert:       rcti
    hor:        rcti
    mask:       rcti
    min:        vec2f
    max:        vec2f
    minzoom:    c_float
    maxzoom:    c_float
    scroll:     c_short  # See: DNA_view2d_types.h
    scroll_ui:  c_short
    keeptot:    c_short
    keepzoom:   c_short
    keepofs:    c_short
    flag:       c_short
    align:      c_short
    win:        vec2s
    oldwin:     vec2s
    around:     c_short

    if version <= (2, 90):
        tab_offset: POINTER(c_float)
        tab_num:    c_int
        tab_cur:    c_int

    alpha_vert: c_char
    alpha_hor:  c_char

    if version >= (2, 93):
        _pad6 = c_char * 6

    sms:            c_void_p  # SmoothView2DStore
    smooth_timer:   lambda: POINTER(wmTimer)


# source\blender\windowmanager\wm_event_system.h
class wmEventHandler(StructBase):  # Generic
    next:   lambda: POINTER(wmEventHandler)
    prev:   lambda: POINTER(wmEventHandler)
    type:   c_int
    flag:   c_char
    poll:   c_void_p

bContext_p = c_void_p   # TODO: Define me
wmDrag_p = c_void_p     # TODO: Define me
Main_p = c_void_p       # TODO: Define me

class wmDropBox(StructBase):
    next: lambda: POINTER(wmDropBox)
    prev: lambda: POINTER(wmDropBox)
    poll: lambda: CFUNCTYPE(c_bool, bContext_p, wmDrag_p, POINTER(wmEvent))
    on_drag_start: lambda: CFUNCTYPE(None, bContext_p, wmDrag_p)
    copy: lambda: CFUNCTYPE(None, bContext_p, wmDrag_p, POINTER(wmDropBox))
    cancel: lambda: CFUNCTYPE(None, Main_p, wmDrag_p, POINTER(wmDropBox))
    draw_droptip: lambda: CFUNCTYPE(None, bContext_p, POINTER(wmWindow), wmDrag_p, (c_int * 2))

    draw_in_view: c_void_p
    draw_activate: c_void_p
    draw_deactivate: c_void_p
    draw_data: c_void_p
    tooltip: c_void_p
    ot: lambda: POINTER(wmOperatorType)
    properties: lambda: POINTER(IDProperty)
    ptr: lambda: POINTER(PointerRNA)


class wmEventHandler_Dropbox(StructBase):
    head:   wmEventHandler
    dropboxes: lambda: POINTER(ListBase(wmDropBox))



# source\blender\makesrna\intern\rna_internal_types.h
class ContainerRNA(StructBase):
    next:       lambda: POINTER(StructRNA)
    prev:       lambda: POINTER(StructRNA)
    prophash:   c_void_p
    properties: ListBase


# source\blender\makesrna\intern\rna_internal_types.h
class StructRNA(StructBase):
    cont:                   ContainerRNA
    identifier:             c_char_p
    py_type:                c_void_p
    blender_type:           c_void_p
    flag:                   c_int
    prop_tag_defines:       c_void_p
    name:                   c_char_p
    description:            c_char_p
    translation_context:    c_char_p
    icon:                   c_int
    nameproperty:           c_void_p
    iteratorproperty:       c_void_p
    base:                   lambda: POINTER(StructRNA)
    nested:                 lambda: POINTER(StructRNA)
    refine:                 c_void_p
    path:                   c_void_p
    reg:                    c_void_p
    unreg:                  c_void_p
    instance:               c_void_p
    idproperties:           c_void_p
    functions:              ListBase


# source\blender\windowmanager\WM_types.h
class wmOperatorType(StructBase):
    name:                   c_char_p
    idname:                 c_char_p
    translation_context:    c_char_p
    description:            c_char_p
    undo_group:             c_char_p
    exec:                   POINTER(c_int)
    check:                  POINTER(c_bool)
    invoke:                 CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p)
    cancel:                 c_void_p
    modal:                  POINTER(c_int)
    poll:                   POINTER(c_bool)
    poll_property:          POINTER(c_bool)
    ui:                     c_void_p
    get_name:               POINTER(c_char_p)
    get_description:        POINTER(c_char_p)
    srna:                   lambda: POINTER(StructRNA)
    last_properties:        c_void_p
    prop:                   c_void_p
    macro:                  c_void_p * 2
    modalkeymap:            c_void_p
    pyop_poll:              POINTER(c_bool)
    rna_ext:                c_void_p * 4

    if version >= (3, 0):
        cursor_pending: c_int

    flag:                   c_short


# source\blender\makesdna\DNA_windowmanager_types.h
class wmOperator(StructBase):
    next:           lambda: POINTER(wmOperator)
    prev:           lambda: POINTER(wmOperator)
    idname:         c_char * 64
    properties:     c_void_p
    type:           lambda: POINTER(wmOperatorType)
    customdata:     c_void_p
    pyinstance:     c_void_p
    ptr:            c_void_p
    reports:        c_void_p
    macro:          c_void_p * 2
    opm:            lambda: POINTER(wmOperator)
    layout:         c_void_p
    flag:           c_short
    _pad6:          c_char * 6


# source\blender\windowmanager\wm_event_system.h
class wmEventHandler_Op(StructBase):

    class op_context(StructBase):
        win:            lambda: POINTER(wmWindow)
        area:           lambda: POINTER(ScrArea)
        region:         lambda: POINTER(ARegion)
        region_type:    c_short

    head:           wmEventHandler
    op:             lambda: POINTER(wmOperator)
    is_file_select: c_bool
    context:        op_context

    del op_context


# source\blender\makesdna\DNA_screen_types.h
class ScrVert(StructBase):
    next:       lambda: POINTER(ScrVert)
    prev:       lambda: POINTER(ScrVert)
    newv:       lambda: POINTER(ScrVert)
    vec:        vec2s
    flag:       c_short
    editflag:   c_short


# source\blender\blenkernel\BKE_screen.h
class SpaceType(StructBase):
    next:                       lambda: POINTER(SpaceType)
    prev:                       lambda: POINTER(SpaceType)
    name:                       c_char * 64  # BKE_ST_MAXNAME
    spaceid:                    c_int
    iconid:                     c_int

    create:                     c_void_p
    free:                       c_void_p
    init:                       c_void_p
    exit:                       c_void_p
    listener:                   c_void_p
    deactivate:                 c_void_p
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

    regiontypes:                ListBase
    keymapflag:                 c_int


# source\blender\makesdna\DNA_screen_types.h
class ScrArea_Runtime(StructBase):
    tool:           c_void_p  # bToolRef
    is_tool_set:    c_char
    _pad0:          c_char * 7


class UAZoneRegion(Union):
    _fields_ = (
        ("edge", c_int),
        ("direction", c_int)
    )


class AZone(StructBase):

    next: lambda: POINTER(AZone)
    prev: lambda: POINTER(AZone)
    region: lambda: POINTER(ARegion)
    type: c_int

    # Union of edge and direction, based on "type"
    _u: UAZoneRegion

    pos: vec2s
    size: vec2s
    rect: rcti
    alpha: c_float


# source\blender\blenkernel\BKE_screen.h
class ARegionType(StructBase):
    next:                       lambda: POINTER(ARegionType)
    prev:                       lambda: POINTER(ARegionType)
    regionid:                   c_int
    init:                       c_void_p
    exit:                       c_void_p
    draw:                       c_void_p

    if version > (2, 83):
        draw_overlay:           c_void_p

    layout:                     c_void_p
    snap_size:                  c_void_p
    listener:                   c_void_p
    message_subscribe:          c_void_p
    free:                       c_void_p
    duplicate:                  c_void_p
    operatortypes:              c_void_p
    keymap:                     c_void_p
    cursor:                     c_void_p
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


# source\blender\makesdna\DNA_screen_types.h
class ARegion(StructBase):
    next:                   lambda: POINTER(ARegion)
    prev:                   lambda: POINTER(ARegion)
    view2D:                 View2D
    winrct:                 rcti
    drawrct:                rcti
    width:                  c_short  # was win[0]
    height:                 c_short  # was win[1]
    visible:                c_short
    regiontype:             c_short
    alignment:              c_short
    flag:                   c_short
    size:                   vec2s  # width/height in unscaled pixels
    do_draw:                c_short
    do_draw_overlay:        c_short
    overlap:                c_short
    flagfullscreen:         c_short
    type:                   lambda: POINTER(ARegionType)  # ARegionType
    uiblocks:               ListBase(uiBlock)
    panels:                 ListBase(Panel)
    panels_category_active: ListBase
    ui_lists:               ListBase
    ui_previews:            ListBase
    handlers:               ListBase(wmEventHandler)
    panels_category:        ListBase


# source\blender\makesdna\DNA_screen_types.h
class bScreen(StructBase):
    id:     lambda: ID
    vertbase: ListBase
    edgebase: ListBase
    areabase: ListBase

    regionbase: ListBase(ARegion)
    scene:  c_void_p  # Scene, DNA_DEPRECATED
    flag: c_short
    winid: c_short
    redraws_flag: c_short
    temp: c_char
    state: c_char
    do_draw: c_char
    do_refresh: c_char
    do_draw_gesture: c_char
    do_draw_paintcursor: c_char
    do_draw_drag: c_char
    skip_handling: c_char
    scrubbing: c_char
    _pad1: c_char * 1
    active_region: lambda: POINTER(ARegion)
    animtimer: lambda: POINTER(wmTimer)
    context: c_void_p
    tooltip: c_void_p  # wmTooltipState
    preview: c_void_p  # PreviewImage


# source\blender\makesdna\DNA_space_types.h
class SpaceLink(StructBase):
    next:           lambda: POINTER(SpaceLink)
    prev:           lambda: POINTER(SpaceLink)
    regionbase:     ListBase(ARegion)
    spacetype:      c_char
    link_flag:      c_char
    _pad0:          c_char * 6


# source\blender\makesdna\DNA_screen_types.h
class ScrArea(StructBase):
    next:                   lambda: POINTER(ScrArea)
    prev:                   lambda: POINTER(ScrArea)
    v1:                     POINTER(ScrVert)
    v2:                     POINTER(ScrVert)
    v3:                     POINTER(ScrVert)
    v4:                     POINTER(ScrVert)
    full:                   POINTER(bScreen)
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
    actionzones:            ListBase(AZone)
    runtime:                ScrArea_Runtime

    _action_zones_cached = None
    @property
    def action_zones(self):
        az = self.actionzones.first
        while az:
            yield az.contents
            az = az.contents.prev


# source\blender\makesdna\DNA_space_types.h
class SpaceText(StructBase):  # SpaceText
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
    _pad2:              c_char
    findstr:            c_char * 256
    replacestr:         c_char * 256
    margin_column:      c_short
    _pad3:              c_char * 2
    runtime:            SpaceText_Runtime


# source\blender\windowmanager\WM_types.h
class wmTabletData(StructBase):
    active:             c_int
    pressure:           c_float
    tilt:               vec2f
    is_motion_absolute: c_char


# source\blender\windowmanager\WM_types.h
class wmEvent(StructBase):
    next:               lambda: POINTER(wmEvent)
    prev:               lambda: POINTER(wmEvent)
    type:               c_short
    val:                c_short
    if version < (3, 2):
        pos:                c_short * 2  # Cursor position in screen coordinates
        mval:               c_short * 2  # Cursor position in region coordinates NOTE: Not always updated
    else:
        pos:                c_int * 2
        mval:               c_int * 2

    utf8_buf:           c_char * 6
    ascii:              c_char

    modifier:           c_char
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


# source\blender\makesdna\DNA_windowmanager_types.h
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
    screen:                 lambda: POINTER(bScreen)  # (deprecated)

    if version >= (2, 93):
        winid:              c_int

    pos:                    vec2s
    size:                   vec2s
    windowstate:            c_char
    active:                 c_char

    if version <= (2, 93):
        _pad0:              c_char * 4

    cursor:                 c_short
    lastcursor:             c_short
    modalcursor:            c_short
    grabcursor:             c_short
    addmousemove:           c_char
    tag_cursor_refresh:     c_char

    if version > (2, 93):
        event_queue_check_click:        c_char
        event_queue_check_drag:         c_char
        event_queue_check_drag_handled: c_char
        _pad0:                          c_char * 1
    else:
        winid:          c_int

    pie_event_type_lock: c_short
    pie_event_type_last: c_short

    eventstate:             lambda: POINTER(wmEvent)
    
    if version >= (3, 2):
        event_last_handled: lambda: POINTER(wmEvent)

    else:
        tweak:                  c_void_p

    ime_data:               c_void_p
    event_queue:            ListBase
    handlers:               ListBase(wmEventHandler)
    modalhandlers:          ListBase(wmEventHandler)
    gesture:                ListBase
    stereo3d_format:        c_void_p
    drawcalls:              ListBase
    cursor_keymap_status:   c_void_p


# source\blender\makesdna\DNA_windowmanager_types.h
class Report(StructBase):
    next:       lambda: POINTER(Report)
    prev:       lambda: POINTER(Report)
    type:       c_short
    flag:       c_short
    len:        c_int
    typestr:    c_char_p
    message:    c_char_p


# source\blender\makesdna\DNA_windowmanager_types.h
class ReportList(StructBase):
    list:           ListBase(Report)
    printlevel:     c_int
    storelevel:     c_int
    flag:           c_int
    _pad4:          c_char * 4
    reporttimer:    lambda: POINTER(wmTimer)


# source\blender\windowmanager\WM_types.h
class wmTimer(StructBase):
    next:       lambda: POINTER(wmTimer)
    prev:       lambda: POINTER(wmTimer)
    win:        lambda: POINTER(wmWindow)

    timestep:   c_double
    event_type: c_int
    flags:      c_int  # wmTimerFlags enum
    customdata: c_void_p
    duration:   c_double
    delta:      c_double
    ltime:      c_double
    ntime:      c_double
    stime:      c_double
    sleep:      c_bool


# source\blender\makesdna\DNA_windowmanager_types.h
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
    reports:                    ReportList
    jobs:                       ListBase
    paintcursors:               ListBase
    drags:                      ListBase
    keyconfigs:                 ListBase

    defaultconf:                c_void_p
    addonconf:                  c_void_p
    userconf:                   c_void_p

    timers:                     ListBase
    autosavetimer:              lambda: POINTER(wmTimer)
    undo_stack:                 c_void_p  # UndoStack
    is_interface_locked:        c_char
    _pad7:                      c_char * 7
    message_bus:                c_void_p  # wmMsgBus
    # ... (cont)


# source\blender\makesdna\DNA_userdef_types.h
class SolidLight(StructBase):
    flag:       c_int
    smooth:     c_float
    _pad0:      c_char * 8
    col:        c_float * 4
    spec:       c_float * 4
    vec:        c_float * 4


# source\blender\makesdna\DNA_userdef_types.h
class CBData(StructBase):
    r:      c_float
    g:      c_float
    b:      c_float
    a:      c_float
    pos:    c_float
    cur:    c_int


# source\blender\makesdna\DNA_userdef_types.h
class ColorBand(StructBase):
    tot:            c_short
    cur:            c_short
    ipotype:        c_char
    ipotype_hue:    c_char
    color_mode:     c_char
    _pad1:          c_char * 1
    data:           lambda: CBData * 32


# source\blender\makesdna\DNA_userdef_types.h
class WalkNavigation(StructBase):
    mouse_speed:        c_float
    walk_speed:         c_float
    walk_speed_factor:  c_float
    view_height:        c_float
    jump_height:        c_float

    teleport_time:      c_float
    flag:               c_short
    _pad0:              c_char * 6


# source\blender\makesdna\DNA_userdef_types.h
class UserDef_SpaceData(StructBase):
    section_active:     c_char
    flag:               c_char
    _pad0:              c_char * 6


# source\blender\makesdna\DNA_userdef_types.h
class UserDef_FileSpaceData(StructBase):
    display_type:       c_int
    thumbnail_size:     c_int
    sort_type:          c_int
    details_flags:      c_int
    flag:               c_int
    _pad0:              c_int
    filter_id:          c_uint64
    temp_win_size:      vec2i


# source\blender\makesdna\DNA_userdef_types.h
class UserDef_Experimental(StructBase):
    use_undo_legacy:                    c_char

    if version < (2, 93):
        use_menu_search:                c_char
        _pad0:                          c_char * 6

    if version > (2, 83):
        no_override_auto_resync:        c_char
        use_cycles_debug:               c_char
        SANITIZE_AFTER_HERE:            c_char
        use_new_hair_type:              c_char
        use_new_point_cloud_type:       c_char

        if version >= (3, 0):
            use_full_frame_compositor:  c_char

        use_sculpt_vertex_colors:       c_char
        use_sculpt_tools_tilt:          c_char

        if version >= (3, 0):
            use_extended_asset_browser: c_char
        else:
            use_asset_browser:          c_char

        use_override_templates:         c_char

        if version >= (3, 0):
            _pad5:                      c_char * 5
        else:
            _pad:                       c_char * 6


# source\blender\makesdna\DNA_userdef_types.h
class UserDef_Runtime(StructBase):
    is_dirty:   c_char
    _pad0:      c_char * 7


# source\blender\makesdna\DNA_userdef_types.h
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

    else:
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
    undosteps:              c_short
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
    color_Picker_type:      c_short
    auto_smoothing_new:     c_char
    ipo_new:                c_char
    keyhandles_new:         c_char
    _pad11:                 c_char * 4

    view_frame_type:        c_char
    view_frame_keyframes:   c_int
    view_frame_seconds:     c_float
    _pad7:                  c_char * 6

    widget_unit:            c_short
    anisotropic_filter:     c_short

    tablet_api:             c_short
    pressure_threshold_max: c_float
    pressure_softness:      c_float
    ndof_sensitivity:       c_float
    ndof_orbit_sensitivity: c_float
    ndof_deadzone:          c_float
    ndof_flag:              c_int

    ogl_multisamples:       c_short
    image_draw_method:      c_short
    glalphaclip:            c_float
    autokey_mode:           c_short
    autokey_flag:           c_short

    if version > (2, 83):
        animation_flag:         c_short

    text_render:            c_char
    navigation_mode:        c_char

    if version < (2, 93):
        _pad9:              c_char * 2

    view_rotate_sensitivity_turntable:  c_float
    view_rotate_sensitivity_trackball:  c_float

    coba_weight:            ColorBand
    sculpt_paint_overlay_col:   c_float * 3
    gpencil_new_layer_col:      c_float * 4

    drag_threshold_mouse: c_char
    drag_threshold_tablet: c_char
    drag_threshold:         c_char
    move_threshold:         c_char

    font_path_ui:       c_char * 1024
    font_path_ui_mono:  c_char * 1024

    compute_device_type:        c_int
    fcu_inactive_alpha:         c_float

    pie_tap_timeout:            c_short
    pie_initial_timeout:        c_short
    pie_animation_timeout:      c_short
    pie_menu_confirm:           c_short
    pie_menu_radius:            c_short
    pie_menu_threshold:         c_short

    opensubdiv_compute_type:    c_short
    _pad6:                      c_short

    factor_display_type:        c_char
    viewport_aa:                c_char
    render_display_type:        c_char
    filebrowser_display_type:   c_char

    sequencer_disk_cache_dir:   c_char * 1024
    seuencer_disk_cache_compression:    c_int
    sequencer_disk_cache_size_limit:    c_int
    sequencer_disk_cache_flag:  c_short

    if version > (2, 83): # check if exists 2.93
        sequencer_proxy_setup:      c_short
        collection_instance_empty_size:     c_float
        _pad10:                     c_char * 3
        statusbar_flag:             c_char

    else:
        _pad5:                      c_char * 2

    walk_navigation:            WalkNavigation
    space_data:                 UserDef_SpaceData
    file_space_data:            UserDef_FileSpaceData
    experimental:               UserDef_Experimental
    runtime:                    UserDef_Runtime
