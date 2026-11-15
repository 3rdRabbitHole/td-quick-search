# Builds the /quick_search component from QuickSearchExt.py.
#
# Run in the TouchDesigner Textport (Alt+T):
#   src = r'<path to this folder>'; exec(open(src + '/build_quick_search.py', encoding='utf-8').read())
#
# The component is self-contained once built: the extension source is copied
# into it, so it can be saved as a .tox and used without these files.
import os

SRC_DIR = globals().get('src') or project.folder
EXT_SOURCE = os.path.join(SRC_DIR, 'QuickSearchExt.py')
if not os.path.isfile(EXT_SOURCE):
	raise FileNotFoundError("QuickSearchExt.py not found in %r - set src to this script's folder" % SRC_DIR)

NAME = 'quick_search'
# One .tox serves both systems, so the Shortcut parameter is left empty by
# default and the keyboard DAT picks the key for the system it runs on.
# Cmd+Tab and Alt+Tab belong to the system on macOS and Windows, and
# TouchDesigner never sees Tab while Control is held on macOS.
DEFAULT_SHORTCUT_EXPR = "('alt.tab' if app.osName == 'macOS' else 'ctrl.tab')"
CONNECT_SHORTCUT = 'shift.tab'
FAMILIES = ['COMP', 'TOP', 'CHOP', 'SOP', 'POP', 'MAT', 'DAT']
MAX_ROWS = 8
WIDTH, SEARCH_H, TAGS_H, ROW_H = 364, 32, 24, 24

old = op('/' + NAME)
settings = {}
if old:
	# keep the user's settings across a rebuild; a parameter left at its
	# default takes the new default
	settings = {p.name: p.eval() for p in old.customPars if not p.isDefault}
	old.destroy()
q = op('/').create(baseCOMP, NAME)
q.nodeX, q.nodeY = 0, -400

page = q.appendCustomPage('Quick Search')
p = page.appendStr('Shortcut', label='Shortcut')[0]
p.default = p.val = ''
p.help = 'Key that opens the popup, e.g. ctrl.tab. Leave empty for the default: ctrl.tab on Windows, alt.tab (Option+Tab) on macOS.'
p = page.appendStr('Connectshortcut', label='Connect Shortcut')[0]
p.default = p.val = CONNECT_SHORTCUT
p.help = 'Key that opens the popup and wires the current operator (green outline) into the new one.'
for name, value in settings.items():
	if hasattr(q.par, name):
		q.par[name] = value


def styleText(t, size, alignx='left', pad=10):
	t.par.fontsizeunits = 'pixels'
	t.par.fontsize = size
	t.par.alignx = alignx
	t.par.textpaddingunits = 'pixels'
	t.par.textpaddingl = pad if alignx == 'left' else 0
	t.par.bgalpha = 1


def dropCallbacks(t):
	cb = t.par.callbacks.eval()
	t.par.callbacks = ''
	if cb:
		cb.destroy()


# extension source, copied in so the component does not depend on the file
ext = q.create(textDAT, 'QuickSearchExt')
ext.text = open(EXT_SOURCE, encoding='utf-8').read()
ext.nodeX, ext.nodeY = -400, 200

# popup panel
popup = q.create(containerCOMP, 'popup')
popup.nodeX, popup.nodeY = 0, 200
popup.par.w, popup.par.h = WIDTH, SEARCH_H + TAGS_H
popup.par.bgcolorr, popup.par.bgcolorg, popup.par.bgcolorb, popup.par.bgalpha = 0.1, 0.1, 0.1, 1
popup.par.align = 'verttb'

# the search field is a real text field so it can own the keyboard focus
search = popup.create(textCOMP, 'search')
search.par.w, search.par.h = WIDTH, SEARCH_H
search.par.alignorder = 0
styleText(search, 15)
search.par.text = ''
search.par.editmode = 'editablecontinuous'
search.par.placeholdertext = 'Search operators...'
search.par.placeholdercolorr = search.par.placeholdercolorg = search.par.placeholdercolorb = 0.4
search.par.bgcolorr = search.par.bgcolorg = search.par.bgcolorb = 0.07
search.nodeX, search.nodeY = 0, 200
searchCallbacks = search.par.callbacks.eval()
if not searchCallbacks:
	searchCallbacks = popup.create(textDAT, 'search_callbacks')
	search.par.callbacks = searchCallbacks.name
searchCallbacks.text = '''def onTextEdit(comp):
	parent.QuickSearch.OnTextEdit(comp.editText)
	return

def onFocusEnd(comp, info):
	parent.QuickSearch.OnFocusEnd(info.get('reason', 'unknown'))
	return
'''
searchCallbacks.nodeX, searchCallbacks.nodeY = 200, 200

tags = popup.create(containerCOMP, 'tags')
tags.par.w, tags.par.h = WIDTH, TAGS_H
tags.par.alignorder = 1
tags.par.align = 'horizlr'
tags.nodeX, tags.nodeY = 0, 0
tagW = WIDTH // len(FAMILIES)
for i, fam in enumerate(FAMILIES):
	t = tags.create(textCOMP, 'tag_' + fam)
	t.par.w, t.par.h = tagW, TAGS_H
	t.par.alignorder = i
	styleText(t, 11, alignx='center')
	dropCallbacks(t)
	t.par.text = fam
	t.par.borderar = t.par.borderag = t.par.borderab = 1
	t.nodeX, t.nodeY = i * 150, 0

for i in range(MAX_ROWS):
	r = popup.create(textCOMP, 'row%d' % i)
	r.par.w, r.par.h = WIDTH, ROW_H
	r.par.alignorder = 2 + i
	styleText(r, 13)
	dropCallbacks(r)
	r.par.text = ''
	r.par.display = False
	r.nodeX, r.nodeY = 0, -200 - i * 150

# clicks on result rows and family tags
pe = q.create(panelexecuteDAT, 'clicks')
pe.par.panels = 'popup/row* popup/tags/tag_*'
pe.par.panelvalue = 'lselect'
pe.par.offtoon = True
pe.text = '''def onOffToOn(panelValue):
	name = panelValue.owner.name
	if name.startswith('row'):
		parent.QuickSearch.OnRowClick(int(name[3:]))
	elif name.startswith('tag_'):
		parent.QuickSearch.OnTagClick(name[4:])
	return
'''
pe.nodeX, pe.nodeY = 200, 0

# borderless window, positioned by the extension
win = q.create(windowCOMP, 'window1')
win.nodeX, win.nodeY = 200, 400
win.par.winop = 'popup'
win.par.title = 'Quick Search'
win.par.borders = False
win.par.alwaysontop = True
win.par.closeescape = False
win.par.justifyoffsetto = 'alldisplays'
win.par.justifyh = 'left'
win.par.justifyv = 'bottom'
win.par.size = 'custom'
win.par.winw, win.par.winh = WIDTH, SEARCH_H + TAGS_H
win.par.cursorvisible = 'alwaysvisible'

# keyboard: the shortcut opens the popup; only the keys the search field
# does not handle itself are listened to
kb = q.create(keyboardinDAT, 'keyboardin1')
kb.nodeX, kb.nodeY = -400, -200
kb.par.shortcuts.expr = ("(parent.QuickSearch.par.Shortcut.eval().strip() or " + DEFAULT_SHORTCUT_EXPR
	+ ") + ' ' + parent.QuickSearch.par.Connectshortcut")
kb.par.keys = 'up down left right esc tab'
kcb = q.create(textDAT, 'keyboard_callbacks')
kcb.nodeX, kcb.nodeY = -200, -200
kcb.text = '''def onKey(dat, key, character, alt, lAlt, rAlt, ctrl, lCtrl, rCtrl, shift, lShift, rShift, state, time, *args, **kwargs):
	parent.QuickSearch.OnKey(key, state)
	return

def onShortcut(dat, shortcutName, time, *args, **kwargs):
	parent.QuickSearch.OnShortcut(shortcutName)
	return
'''
kb.par.callbacks = 'keyboard_callbacks'
auto = q.op('keyboardin1_callbacks')
if auto:
	auto.destroy()

# extension hookup
q.par.parentshortcut = 'QuickSearch'
q.par.ext0object = "op('./QuickSearchExt').module.QuickSearchExt(me)"
q.par.ext0name = 'QuickSearchExt'
q.par.ext0promote = True
q.par.reinitextensions.pulse()
