# This module holds common macro defines and enums for DNA.


# DNA_windowmanager_types.h
OPERATOR_RUNNING_MODAL = 1 << 0
OPERATOR_CANCELLED     = 1 << 1
OPERATOR_FINISHED      = 1 << 2
OPERATOR_PASS_THROUGH  = 1 << 3


# source/blender/windowmanager/WM_types.h
# wmOperatorType.flag
OPTYPE_REGISTER          = 1 << 0
OPTYPE_UNDO              = 1 << 1
OPTYPE_BLOCKING          = 1 << 2
OPTYPE_MACRO             = 1 << 3
OPTYPE_GRAB_CURSOR_XY    = 1 << 4
OPTYPE_GRAB_CURSOR_X     = 1 << 5
OPTYPE_GRAB_CURSOR_Y     = 1 << 6
OPTYPE_PRESET            = 1 << 7
OPTYPE_INTERNAL          = 1 << 8
OPTYPE_LOCK_BYPASS       = 1 << 9
OPTYPE_UNDO_GROUPED      = 1 << 10
OPTYPE_DEPENDS_ON_CURSOR = 1 << 11


# source/blender/makesdna/DNA_space_types.h
# eSpaceText_Flags
ST_SCROLL_SELECT = 1 << 0
ST_FLAG_UNUSED_4 = 1 << 4
ST_FIND_WRAP     = 1 << 5
ST_FIND_ALL      = 1 << 6
ST_SHOW_MARGIN   = 1 << 7
ST_MATCH_CASE    = 1 << 8
ST_FIND_ACTIVATE = 1 << 9


# source/blender/makesdna/DNA_space_types.h
# eSpace_Type
SPACE_EMPTY       = 0
SPACE_VIEW3D      = 1
SPACE_GRAPH       = 2
SPACE_OUTLINER    = 3
SPACE_PROPERTIES  = 4
SPACE_FILE        = 5
SPACE_IMAGE       = 6
SPACE_INFO        = 7
SPACE_SEQ         = 8
SPACE_TEXT        = 9
SPACE_ACTION      = 12
SPACE_NLA         = 13
SPACE_NODE        = 16
SPACE_CONSOLE     = 18
SPACE_USERPREF    = 19
SPACE_CLIP        = 20
SPACE_TOPBAR      = 21
SPACE_STATUSBAR   = 22
SPACE_SPREADSHEET = 23


# source/blender/makesdna/DNA_screen_types.h
# eRegion_Type
RGN_TYPE_WINDOW      = 0
RGN_TYPE_HEADER      = 1
RGN_TYPE_CHANNELS    = 2
RGN_TYPE_TEMPORARY   = 3
RGN_TYPE_UI          = 4
RGN_TYPE_TOOLS       = 5
RGN_TYPE_TOOL_PROPS  = 6
RGN_TYPE_PREVIEW     = 7
RGN_TYPE_HUD         = 8
RGN_TYPE_NAV_BAR     = 9
RGN_TYPE_EXECUTE     = 10
RGN_TYPE_FOOTER      = 11
RGN_TYPE_TOOL_HEADER = 12
RGN_TYPE_XR          = 13


area_to_enum = {
    'EMPTY':            SPACE_EMPTY,
    'VIEW_3D':          SPACE_VIEW3D,
    'IMAGE_EDITOR':     SPACE_IMAGE,
    'NODE_EDITOR':      SPACE_NODE,
    'SEQUENCE_EDITOR':  SPACE_SEQ,
    'CLIP_EDITOR':      SPACE_CLIP,
    'DOPESHEET_EDITOR': SPACE_ACTION,
    'GRAPH_EDITOR':     SPACE_GRAPH,
    'NLA_EDITOR':       SPACE_NLA,
    'TEXT_EDITOR':      SPACE_TEXT,
    'CONSOLE':          SPACE_CONSOLE,
    'INFO':             SPACE_INFO,
    'TOPBAR':           SPACE_TOPBAR,
    'OUTLINER':         SPACE_OUTLINER,
    'PROPERTIES':       SPACE_PROPERTIES,
    'FILE_BROWSER':     SPACE_FILE,
    'SPREADSHEET':      SPACE_SPREADSHEET,
    'PREFERENCES':      SPACE_USERPREF,
}.__getitem__


region_to_enum = {
    "WINDOW": RGN_TYPE_WINDOW,
    "HEADER": RGN_TYPE_HEADER,
    "CHANNELS": RGN_TYPE_CHANNELS,
    "TEMPORARY": RGN_TYPE_TEMPORARY,
    "UI": RGN_TYPE_UI,
    "TOOLS": RGN_TYPE_TOOLS,
    "TOOL_PROPS": RGN_TYPE_TOOL_PROPS,
    "PREVIEW": RGN_TYPE_PREVIEW,
    "HUD": RGN_TYPE_HUD,
    "NAVIGATION_BAR": RGN_TYPE_NAV_BAR,
    "EXECUTE": RGN_TYPE_EXECUTE,
    "FOOTER": RGN_TYPE_FOOTER,
    "TOOL_HEADER": RGN_TYPE_TOOL_HEADER,
}.__getitem__


# source/blender/makesdna/DNA_text_types.h
TXT_ISDIRTY       = 1 << 0
TXT_ISMEM         = 1 << 2
TXT_ISEXT         = 1 << 3
TXT_ISSCRIPT      = 1 << 4
TXT_FLAG_UNUSED_8 = 1 << 8
TXT_FLAG_UNUSED_9 = 1 << 9
TXT_TABSTOSPACES  = 1 << 10