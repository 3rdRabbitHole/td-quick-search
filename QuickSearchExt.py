"""
Quick Search - a minimal operator search/create popup for TouchDesigner.

Ctrl+Tab in a network editor opens a one-line search bar at the mouse.
Type 2+ characters to list matching operators. Up/Down picks a name,
Left/Right (or Tab / Shift+Tab) picks a family, Enter places the node
at the position the mouse had when the popup was opened.
"""

FAMILIES = ['COMP', 'TOP', 'CHOP', 'SOP', 'POP', 'MAT', 'DAT']
MAX_ROWS = 8
MIN_CHARS = 2

WIDTH = 364
SEARCH_H = 32
TAGS_H = 24
ROW_H = 24

BG_ROW = (0.13, 0.13, 0.13)
BG_ROW_SEL = (0.22, 0.34, 0.52)
TAG_DIM_BG = (0.13, 0.13, 0.13)
TAG_DIM_FONT = (0.36, 0.36, 0.36)
FALLBACK_COLOR = (0.35, 0.35, 0.35)


class QuickSearchExt:

	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self.popup = ownerComp.op('popup')
		self.search = ownerComp.op('popup/search')
		self.window = ownerComp.op('window1')
		self.mouse = ownerComp.op('mousein1')
		self.query = ''
		self.results = []
		self.rowIndex = 0
		self.family = None
		self.preferred = None
		self.lastFamily = 'TOP'
		self.isOpen = False
		self.shiftDown = False
		self.session = 0
		self.target = None
		self.nodePos = (0, 0)
		self.screenPos = (0, 0)
		self.index = []
		self.buildIndex()

	# ------------------------------------------------------------ index

	def buildIndex(self):
		byLabel = {}
		for fam in FAMILIES:
			for cls in families.get(fam, []):
				label = getattr(cls, 'label', None)
				if not label:
					continue
				entry = byLabel.setdefault(label.lower(), {'label': label, 'fams': {}})
				entry['fams'][fam] = cls
		self.index = []
		for key, entry in byLabel.items():
			words = key.split()
			entry['words'] = words
			entry['compact'] = ''.join(words)
			entry['initials'] = ''.join(w[0] for w in words)
			self.index.append(entry)

	def score(self, entry, tokens, compactQuery):
		compact = entry['compact']
		words = entry['words']
		if compact.startswith(compactQuery):
			return 0
		if any(w.startswith(compactQuery) for w in words):
			return 1
		if len(words) > 1 and entry['initials'].startswith(compactQuery):
			return 2
		if len(tokens) > 1 and self.matchWordStarts(words, tokens):
			return 2
		if compactQuery in compact:
			return 3
		return None

	@staticmethod
	def matchWordStarts(words, tokens):
		# every token must start a word, in order ("m f o" -> Movie File Out)
		i = 0
		for token in tokens:
			while i < len(words) and not words[i].startswith(token):
				i += 1
			if i == len(words):
				return False
			i += 1
		return True

	def Search(self, query):
		tokens = query.lower().split()
		compactQuery = ''.join(tokens)
		if len(compactQuery) < MIN_CHARS:
			return []
		found = []
		for entry in self.index:
			s = self.score(entry, tokens, compactQuery)
			if s is not None:
				found.append((s, len(entry['compact']), entry['label'], entry))
		found.sort(key=lambda t: t[:3])
		return [t[3] for t in found[:MAX_ROWS]]

	# ------------------------------------------------------ open / close

	def Toggle(self):
		if self.isOpen:
			self.Close()
		else:
			self.Open()

	def Open(self):
		pane = ui.panes.current
		if pane is None or pane.type != PaneType.NETWORKEDITOR:
			return
		mx, my = self.mouse['tx'].eval(), self.mouse['ty'].eval()
		bl, tr = pane.bottomLeft, pane.topRight
		# mouse (desktop pixels) -> network units; 8 = window frame thickness
		cx = ui.windowX + 8 + (bl.x + tr.x) / 2
		cy = ui.windowY + 8 + (bl.y + tr.y) / 2
		self.nodePos = (pane.x + (mx - cx) / pane.zoom, pane.y + (my - cy) / pane.zoom)
		self.screenPos = (mx, my)
		self.target = pane.owner

		selected = [c for c in self.target.selectedChildren if c.family in FAMILIES]
		self.preferred = selected[0].family if selected else self.lastFamily
		self.query = ''
		self.results = []
		self.rowIndex = 0
		self.session += 1
		self.isOpen = True
		self.search.par.text = ''
		self.Refresh()
		self.window.par.winopen.pulse()
		self.focusSearch(3)

	def Close(self):
		self.isOpen = False
		self.window.par.winclose.pulse()

	def focusSearch(self, delayFrames=1):
		# The search field must own the keyboard: while it is being edited
		# TouchDesigner routes keys to it instead of the network editor, so
		# typing does not trigger network shortcuts (delete, bypass, Tab...).
		run("args[0].focusNow(args[1])", self, self.session, delayFrames=delayFrames)

	def focusNow(self, session):
		if self.isOpen and session == self.session:
			self.search.setKeyboardFocus()

	# ------------------------------------------- search field callbacks

	def OnTextEdit(self, text):
		if not self.isOpen:
			return
		self.query = text
		self.results = self.Search(text)
		self.rowIndex = 0
		self.Refresh()

	def OnFocusEnd(self, reason):
		if not self.isOpen:
			return
		if reason == 'enter':
			if self.results:
				self.Place()
			else:
				self.Close()
		elif reason == 'escape':
			self.Close()
		elif reason == 'tab':
			self.cycleFamily(-1 if self.shiftDown else 1)
			self.focusSearch()
		else:
			# clicked somewhere else; give a click on a row or tag the
			# chance to place the node before closing
			run("args[0].closeIfSession(args[1])", self, self.session, delayFrames=5)

	def closeIfSession(self, session):
		if self.isOpen and session == self.session:
			self.Close()

	# ------------------------------------------------------------- keys

	def OnKey(self, key, shift, state):
		self.shiftDown = bool(shift)
		if not self.isOpen or not state:
			return
		if key == 'up':
			self.moveRow(-1)
		elif key == 'down':
			self.moveRow(1)
		elif key == 'left':
			self.cycleFamily(-1)
		elif key == 'right':
			self.cycleFamily(1)

	def moveRow(self, step):
		if self.results:
			self.rowIndex = (self.rowIndex + step) % len(self.results)
			self.Refresh()

	def available(self):
		if not self.results:
			return []
		fams = self.results[self.rowIndex]['fams']
		return [f for f in FAMILIES if f in fams]

	def cycleFamily(self, step):
		avail = self.available()
		if len(avail) < 2:
			return
		i = avail.index(self.family) if self.family in avail else 0
		self.family = avail[(i + step) % len(avail)]
		self.preferred = self.family
		self.Refresh()

	def resolveFamily(self):
		avail = self.available()
		if not avail:
			self.family = None
		elif self.preferred in avail:
			self.family = self.preferred
		elif self.lastFamily in avail:
			self.family = self.lastFamily
		else:
			self.family = avail[0]

	# ------------------------------------------------------------ mouse

	def OnRowClick(self, i):
		if self.isOpen and i < len(self.results):
			self.rowIndex = i
			self.resolveFamily()
			self.Place()

	def OnTagClick(self, fam):
		if not self.isOpen:
			return
		if fam in self.available():
			self.family = fam
			self.Place()
		else:
			# a click on an inactive tag should not dismiss the popup
			self.session += 1
			self.focusSearch()

	# ------------------------------------------------------------ place

	def Place(self):
		if not self.results or self.family is None or self.target is None:
			return
		entry = self.results[self.rowIndex]
		cls = entry['fams'][self.family]
		ui.undo.startBlock('Quick Search: %s %s' % (entry['label'], self.family))
		try:
			node = self.target.create(cls)
			node.nodeCenterX, node.nodeCenterY = self.nodePos
			for c in self.target.selectedChildren:
				c.selected = False
			node.selected = True
			node.current = True
		finally:
			ui.undo.endBlock()
		self.lastFamily = self.family
		self.Close()

	# ---------------------------------------------------------- display

	def Refresh(self):
		self.resolveFamily()
		popup = self.popup

		for i in range(MAX_ROWS):
			row = popup.op('row%d' % i)
			if i < len(self.results):
				row.par.display = True
				row.par.text = self.results[i]['label']
				r, g, b = BG_ROW_SEL if i == self.rowIndex else BG_ROW
				row.par.bgcolorr, row.par.bgcolorg, row.par.bgcolorb = r, g, b
			else:
				row.par.display = False

		avail = self.available()
		for fam in FAMILIES:
			tag = popup.op('tags/tag_' + fam)
			if fam in avail:
				color = ui.colors[fam] if fam in ui.colors else FALLBACK_COLOR
				current = fam == self.family
				gain = 1.3 if current else 0.8
				bg = tuple(min(1.0, c * gain + (0.08 if current else 0.04)) for c in color)
				font = (1, 1, 1) if current else (0.85, 0.85, 0.85)
				tag.par.bold = current
				tag.par.bottomborder = 'bordera' if current else 'off'
			else:
				bg, font = TAG_DIM_BG, TAG_DIM_FONT
				tag.par.bold = False
				tag.par.bottomborder = 'off'
			tag.par.bgcolorr, tag.par.bgcolorg, tag.par.bgcolorb = bg
			tag.par.fontcolorr, tag.par.fontcolorg, tag.par.fontcolorb = font

		h = SEARCH_H + TAGS_H + ROW_H * len(self.results)
		popup.par.h = h
		win = self.window
		win.par.winw, win.par.winh = WIDTH, h
		# keep the top-left corner pinned at the mouse position
		win.par.winoffsetx = self.screenPos[0]
		win.par.winoffsety = self.screenPos[1] - h
