# The MIT License (MIT)
# 
# Copyright (c) 2015 Josef Gajdusek
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import collections
import random
import string
from math import ceil, floor
from wytch import colors, canvas, event

HOR_LEFT = 1
HOR_MID = 2
HOR_RIGHT = 3

VER_TOP = 1
VER_MID = 2
VER_BOT = 3

class View(event.EventSource):

    def __init__(self):
        super(View, self).__init__()
        self.onupdate = None
        self.zindex = 0
        self._focused = False
        self._canvas = None
        self.parent = None
        self._focusable = True
        self._vstretch = True
        self._hstretch = True
        self.display = True
        self._dirty = True

    def bubble(self, event):
        """ Bubble an event from this to the root or until .fire() succeeds """
        if not self.fire(event) and self.parent:
            self.parent.bubble(event)

    def onfocus(self):
        pass

    def onunfocus(self):
        pass

    def onchildfocused(self, c):
        pass

    @property
    def root(self):
        if self.parent:
            return self.parent.root
        else:
            return self

    @property
    def focused_child(self):
        return None

    @property
    def focused_leaf(self):
        if self.focused_child:
            return self.focused_child.focused_leaf
        return self

    @property
    def focused(self):
        return self._focused

    @focused.setter
    def focused(self, f):
        if self._focused == f:
            return
        if f and not self.focusable:
            raise NotImplementedError("This view is not focusable")
        self._focused = f
        # Bubble up until the root
        if f:
            self.onfocus()
            if self.parent:
                # Unfocus other children of parent
                self.parent.onchildfocused(self)
        else:
            self.onunfocus()

    @property
    def canvas(self):
        return self._canvas

    @canvas.setter
    def canvas(self, c):
        self._canvas = c
        self.recalc()

    def update(self):
        """Wakes the render thread to perform at least one render cycle"""
        if self.root.onupdate:
            self.root.onupdate()

    def precalc(self):
        """Called before new canvas gets assigned, mostly used by children
        to update their size.
        """
        pass

    def recalc(self):
        """Called on canvas change"""
        pass

    def render(self):
        pass

    @property
    def hstretch(self):
        return self._hstretch

    @hstretch.setter
    def hstretch(self, h):
        self._hstretch = h

    @property
    def vstretch(self):
        return self._vstretch

    @vstretch.setter
    def vstretch(self, v):
        self._vstretch = v

    @property
    def size(self):
        return (0, 0)

    @property
    def focusable(self):
        return self._focusable

    @focusable.setter
    def focusable(self, f):
        self._focusable = f

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, d):
        self._dirty = d
        if d:
            self.update()

    def __str__(self):
        return "<%s.%s zindex = %d focused = %r focusable = %r size = %r>" % \
                (self.__class__.__name__, self.__class__.__module__,
                        self.zindex, self.focused, self.focusable, self.size)


class ContainerView(View):

    def __init__(self, canvas = None):
        super(ContainerView, self).__init__()
        self.children = []
        self._shouldclear = True

    def onfocus(self):
        super(ContainerView, self).onfocus()
        # Focus first focusable child
        if len(self.children) > 0:
            for c in self.children:
                if c.focusable and c.display:
                    c.focused = True

    def onunfocus(self):
        super(ContainerView, self).onunfocus()
        for c in self.children:
            c.focused = False

    def onchildfocused(self, cf):
        super(ContainerView, self).onchildfocused(cf)
        for c in self.children:
            if c.focused and c != cf:
                c.focused = False
        self._focused = True
        if self.parent:
            self.parent.onchildfocused(self)

    def _focused_child_index(self):
        for i, c in enumerate(self.children):
            if c.focused:
                return i, c
        return None, None

    @property
    def focused_child(self):
        _, c = self._focused_child_index()
        return c

    @event.handler("key", canreject = True, keys = ["<up>", "<down>", "\t"])
    def _onkey(self, kc):
        # See if child can handle the event
        if self.focused_child and self.focused_child.fire(kc):
            return True
        # Can we handle it?
        if kc.val == "<up>" or kc.val == "\t" and kc.shift:
            return self.focus_prev()
        elif kc.val in ["<down>", "\t"]:
            return self.focus_next()
        return False

    @event.handler("mouse")
    def _onmouse(self, me):
        if not self.children:
            return
        z = self.children[-1].zindex
        # Pass the event only to children on the top zindex
        for c in self.children[::-1]:
            if c.zindex != z:
                break
            sme = me.shifted(c.canvas.x, c.canvas.y)
            # Will be always true for ContainerView, but could be false for subclasses
            if c.canvas.contains(sme.x, sme.y):
                c.fire(sme)

    def focus_next(self, step = 1):
        if len(self.children) == 0:
            return
        i, c = self._focused_child_index()
        if not i:
            i = 0

        i += step
        while i in range(0, len(self.children)):
            if self.children[i].focusable and self.children[i].display and \
                    (not c or self.children[i].zindex == c.zindex):
                self.children[i].focused = True
                return True
            i += step
        return False

    def focus_prev(self):
        return self.focus_next(step = -1)

    def add_child(self, c):
        c.parent = self
        self.children.append(c)
        self.dirty = True

    def remove_child(self, c):
        f = c.focused
        c.parent = None
        c.focused = False
        self.children.remove(c)
        if f:
            self.onfocus()
        self.dirty = True

    def precalc(self):
        if self.dirty:
            for c in self.children:
                c.precalc()

    def recalc(self):
        """Called on canvas change an addition/removal of a child"""
        if self.dirty:
            self.children.sort(key = lambda x: x.zindex)
            for c in self.children:
                c.canvas = self.canvas
            self._shouldclear = True
            self.dirty = False

    def render(self):
        if self._shouldclear:
            self._shouldclear = False
            self.canvas.clear(blank = True)
        for c in self.children:
            if c.display:
                c.render()

    @property
    def focusable(self):
        return any([c.focusable for c in self.children])

    @property
    def size(self):
        if not self.children:
            return (0, 0)
        return (max(c.size[0] for c in self.children),
                max(c.size[1] for c in self.children))

    @property
    def hstretch(self):
        return any(c.hstretch for c in self.children)

    @property
    def vstretch(self):
        return any(c.vstretch for c in self.children)

    @property
    def dirty(self):
        return self._dirty or any(c.dirty for c in self.children)

    @dirty.setter
    def dirty(self, d):
        self._dirty = d
        for c in self.children:
            c.dirty = d


class Align(ContainerView):

    def __init__(self, halign = HOR_MID, valign = VER_MID):
        super(Align, self).__init__()
        self.halign = halign
        self.valign = valign

    def recalc(self):
        if self.halign == HOR_LEFT:
            x = 0
        elif self.halign == HOR_MID:
            x = int(self.canvas.width / 2 - self.size[0] / 2)
        else:
            x = self.canvas.width - self.size[0]
        if self.valign == VER_TOP:
            y = 0
        elif self.valign == VER_MID:
            y = int(self.canvas.height / 2 - self.size[1] / 2)
        else:
            y = self.canvas.height - self.size[1]
        subc = canvas.SubCanvas(self.canvas, x, y, self.size[0], self.size[1])
        for c in self.children:
            c.canvas = subc

    def __str__(self):
        if self.halign == HOR_LEFT:
            hstr = "HOR_LEFT"
        elif self.halign == HOR_MID:
            hstr = "HOR_MID"
        else:
            hstr = "HOR_RIGHT"
        if self.valign == VER_TOP:
            vstr = "VER_TOP"
        elif self.valign == VER_MID:
            vstr = "VER_MID"
        else:
            vstr = "VER_BOT"
        return "<%s.%s zindex = %d focused = %r focusable = %r size = %r " \
                "halign = %s valign = %s>" % \
                (self.__class__.__name__, self.__class__.__name__,
                    self.zindex, self.focused, self.focusable, self.size,
                    hstr, vstr)


class Box(ContainerView):

    def __init__(self, title = None, bg = colors.BLACK):
        super(Box, self).__init__()
        self.title = title
        self.bg = bg

    def recalc(self):
        subc = canvas.SubCanvas(self.canvas, 2, 1,
                self.canvas.width - 4, self.canvas.height - 2)
        for c in self.children:
            c.canvas = subc

    def render(self):
        self.canvas.clear()
        super(Box, self).render()
        self.canvas.box(0, 0, self.canvas.width - 1, self.canvas.height - 1,
                bg = self.bg)
        if self.title:
            self.canvas.text(1, 0, " " + self.title + " ")

    @property
    def size(self):
        w, h = super(Box, self).size
        w += 4
        h += 2
        if self.title:
            w = max(w, len(self.title) + 4)
        return (w, h)

    def __str__(self):
        return "<%s.%s zindex = %d focused = %r focusable = %r size = %r " \
                "title = \"%s\" bg = %r>" % \
                (self.__class__.__name__, self.__class__.__name__,
                    self.zindex, self.focused, self.focusable, self.size,
                    self.title, self.bg)


class Vertical(ContainerView):

    def __init__(self, width = 0):
        super(Vertical, self).__init__()
        self._width = width
        self._height = 0

    def recalc(self):
        anyc = sum(c.vstretch for c in self.children)
        remh = self.canvas.height - sum(c.size[1] for c in self.children)
        perc = round(remh / anyc) if anyc else 0
        h = 0
        for c in self.children:
            ch = c.size[1]
            if ch == 0:
                continue
            if c.vstretch: # "Any height"
                if remh > perc:
                    ch = perc
                else:
                    ch = remh
                remh -= ch
                ch += c.size[1]
            c.canvas = canvas.SubCanvas(self.canvas, 0, h, self.canvas.width, ch)
            h += ch

    @property
    def size(self):
        if not self.children:
            return (0, 0)
        return (max(c.size[0] for c in self.children),
                sum(c.size[1] for c in self.children))


class Horizontal(ContainerView):

    def __init__(self, height = 0):
        super(Horizontal, self).__init__()
        self._height = height

    def recalc(self):
        anyc = sum(c.hstretch for c in self.children)
        remw = self.canvas.width - sum(c.size[0] for c in self.children)
        perc = round(remw / anyc) if anyc else 0
        w = 0
        for c in self.children:
            cw = c.size[0]
            if cw == 0:
                continue
            if c.hstretch: # "Any width"
                if remw > perc:
                    cw = perc
                else:
                    cw = remw
                remw -= cw
                cw += c.size[0]
            c.canvas = canvas.SubCanvas(self.canvas, w, 0, cw, self.canvas.height)
            w += cw

    @property
    def size(self):
        if not self.children:
            return (0, 0)
        return (sum(c.size[0] for c in self.children),
                max(c.size[1] for c in self.children))


class Grid(ContainerView):

    class Cell:

        def __init__(self, child, colspan, rowspan):
            self.child = child
            self.colspan = colspan
            self.rowspan = rowspan

    def __init__(self, width, height):
        super(Grid, self).__init__()
        self.width = width
        self.height = height
        self.grid = [[None] * width for _ in range(height)]
        self._size = (0, 0)

    def onfocus(self):
        if any([c.focused for c in self.children]):
            return # The focus came from child
        # Focus first focusable child starting from top left and walking by columns first
        for y in range(self.height):
            for x in range(self.width):
                c = self.grid[y][x]
                if c and c.child.focusable and c.child.display:
                    c.child.focused = True
                    return

    def set(self, x, y, child, colspan = 1, rowspan = 1):
        if self.grid[y][x]:
            self.remove_child(self.grid[y][x].child)
        self.grid[y][x] = Grid.Cell(child, colspan, rowspan)
        self.add_child(child)

    def precalc(self):
        # Iterate over all colspans
        self._cws = [0] * self.width # Column widths
        for colspan in range(1, self.width + 1):
            for i, col in enumerate(zip(*self.grid)):
                for ch in col:
                    if not ch or ch.colspan != colspan:
                        continue
                    tot = 0
                    # Over all affected columns
                    for oc in range(ch.colspan):
                        tot += self._cws[i + oc]
                    if tot < ch.child.size[0]: # else the child fits into the allocated space already
                        over = ch.child.size[0] - tot
                        spl = floor(over / ch.colspan)
                        # Evenly grow all columns to contain this element
                        for oc in range(ch.colspan):
                            self._cws[i + oc] += spl
                            over -= spl
                        # Split the rest, prefer to grow rightmost
                        for oc in range(ch.colspan - 1, 0, -1):
                            if over <= 0:
                                break
                            self._cws[i + oc] += 1
                            over -= 1
        self._rhs = [0] * self.height
        # Iterate over all possible rowspans
        for rowspan in range(1, self.height + 1):
            for i, row in enumerate(self.grid):
                for ch in row:
                    if not ch or ch.rowspan != rowspan:
                        continue
                    tot = 0
                    # Over all affected columns
                    for oc in range(ch.rowspan):
                        tot += self._rhs[i + oc]
                    if tot < ch.child.size[1]: # else the child fits into the allocated space already
                        over = ch.child.size[1] - tot
                        spl = floor(over / ch.rowspan)
                        # Evenly grow all columns to contain this element
                        for oc in range(ch.rowspan):
                            self._rhs[i + oc] += spl
                            over -= spl
                        # Split the rest, prefer to grow rightmost
                        for oc in range(ch.rowspan - 1, 0, -1):
                            if over <= 0:
                                break
                            self._rhs[i + oc] += 1
                            over -= 1
        self._size = (sum(self._cws), sum(self._rhs))

    def recalc(self):
        aty = 0
        # Assign subcanvases
        for ri, row in enumerate(self.grid):
            atx = 0
            for ci, c in enumerate(row):
                if c:
                    w = 0
                    for x in self._cws[ci:ci + c.colspan]:
                        w += x
                    h = 0
                    for x in self._rhs[ri:ri + c.rowspan]:
                        h += x
                    assert w >= c.child.size[0] and h >= c.child.size[1]
                    c.child.canvas = \
                            canvas.SubCanvas(self.canvas, atx, aty,
                                    w, h)
                atx += self._cws[ci]
            aty += self._rhs[ri]

    @property
    def size(self):
        return self._size

    def __str__(self):
        return "<%s.%s zindex = %d focused = %r focusable = %r size = %r " \
                "width = %d height = %d>" % \
                (self.__class__.__module__, self.__class__.__name__,
                        self.zindex, self.focused, self.focusable,
                        self.width, self.height)


class HLine(View):

    def __init__(self, title = None):
        super(HLine, self).__init__()
        self.title = title
        self.focusable = None
        self.vstretch = False

    def render(self):
        self.canvas.hline(0, 0, self.canvas.width)
        if self.title:
            self.canvas.text(0, 0, self.title + " ")

    @property
    def size(self):
        return (len(self.title) if self.title else 1, 1)

    def __str__(self):
        return "<%s.%s zindex = %d focused = %r focusable = %r size = %r " \
                "title = \"%s\">" % \
                (self.__class__.__module__, self.__class__.__name__,
                    self.zindex, self.focused, self.focusable, self.title)


class Spacer(View):

    def __init__(self, width = 1, height = 1, hstretch = False, vstretch = False):
        super(Spacer, self).__init__()
        self.focusable = False
        self.width = width
        self.height = height
        self.hstretch = hstretch
        self.vstretch = vstretch

    @property
    def size(self):
        return (self.width, self.height)


class Widget(View):

    @event.handler("mouse", pressed = True, button = event.MouseEvent.LEFT)
    def _onmouse(self, me):
        if self.focusable:
            if self.focusable and not self.focused:
                self.focused = True
            else:
                self.fire(event.ClickEvent())

    def onfocus(self):
        super(Widget, self).onfocus()
        self.update()

    def onunfocus(self):
        super(Widget, self).onunfocus()
        self.update()


class ValueWidget(Widget):

    def __init__(self, value = None, onvalue = None):
        super(ValueWidget, self).__init__()
        self._value = value
        if onvalue:
            self.bind("value", onvalue)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        if self._value == v:
            return
        ev = event.ValueEvent(v, old = self._value, source = self)
        self._value = v
        self.fire(ev)
        self.update()


class Label(Widget):

    def __init__(self, text = "Label", fg = colors.WHITE, bg = colors.BLACK):
        super(Label, self).__init__()
        self.fg = fg
        self.bg = bg
        self.text = text
        self.focusable = False
        self.vstretch = False

    def render(self):
        self.canvas.text(0, 0, self.text, fg = self.fg, bg = self.bg)

    @property
    def size(self):
        return (len(self.text), 1)

    def __str__(self):
        return "<%s.%s zindex = %d focused = %r focusable = %r size = %r " \
                "text = \"%s\" fg = %r bg = %r>" % \
                (self.__class__.__module__, self.__class__.__name__,
                    self.zindex, self.focused, self.focusable, self.size,
                    self.text, self.fg, self.bg)


class Button(Widget):

    def __init__(self, label = "Button", onpress = None):
        super(Widget, self).__init__()
        self.label = label
        self.vstretch = False
        if onpress:
            self.bind("press", onpress)

    @event.handler("click")
    @event.handler("key", key = "\r")
    def _onclick(self, me):
        self.fire(event.PressEvent(self))

    def render(self):
        if self.focused:
            txt = "> " + self.label + " <"
        else:
            txt = "  " + self.label + "  "
        offs = floor(self.canvas.width / 2 - len(txt) / 2)
        self.canvas.text(offs, 0, txt,
                fg = colors.WHITE, bg = colors.BLACK,
                flags = canvas.NEGATIVE if self.focused else 0)

    @property
    def size(self):
        return (len(self.label) + 4, 1)

    def __str__(self):
        return "<%s.%s zindex = %d focused = %r focusable = %r size = %r " \
                "label = \"%s\">" % \
                (self.__class__.__module__, self.__class__.__name__,
                    self.zindex, self.focused, self.focusable, self.size, self.label)


class TextInput(ValueWidget):

    def __init__(self, default = "", length = 12, onvalue = None,
            password = False):
        super(TextInput, self).__init__(value = default, onvalue = onvalue)
        self.length = length
        self.value = default
        self.offset = 0
        self.cursor = len(self.value)
        self.password = password
        self.vstretch = False

    @event.handler("key", key = "\x7f")
    def _onbackspace(self, kc):
        if self.cursor > 0:
            self.cursor -= 1
            self.offset -= 1
            self.value = self.value[:self.cursor] + self.value[self.cursor+1:]

    @event.handler("key", key = "<delete>")
    def _ondelete(self, kc):
        if len(self.value):
            self.value = self.value[:self.cursor] + self.value[self.cursor+1:]

    @event.handler("key", key = "<left>")
    def _onleft(self, kc):
        if self.cursor > 0:
            self.cursor -= 1
            if self.cursor < self.offset:
                self.offset -= 1

    @event.handler("key", key = "<right>")
    def _onright(self, kc):
        if self.cursor < len(self.value):
            self.cursor += 1
            if self.cursor > self.offset + self.length - 1:
                self.offset += 1

    @event.handler("key", key = "<home>")
    def _onhome(self, kc):
        self.cursor = 0
        self.offset = 0

    @event.handler("key", key = "<end>")
    def _onend(self, kc):
        self.cursor = len(self.value)
        self.offset = len(self.value) - self.length + 1

    @event.handler("key", matcher = lambda ke: len(ke.val) == 1 and ke.val in string.printable \
                                               and ke.val not in "\r\n\t\x0b\x0c")
    def _onkey(self, kc):
        self.cursor += 1
        if self.cursor > self.offset + self.length - 1:
            self.offset += 1
        self.value = self.value[:self.cursor-1] + kc.val + \
                self.value[self.cursor-1:]

    def render(self):
        self.canvas.clear()
        flg = canvas.UNDERLINE | (canvas.BOLD if self.focused else canvas.FAINT)
        for i in range(
                max(self.length,
                len(self.value) + (self.length - (len(self.value) - self.offset)))):
            if i >= len(self.value):
                c = " "
            elif self.password:
                c = "*"
            else:
                c = self.value[i]
            x = i - self.offset
            if x < 0 or x >= self.length:
                c = ""
                x = 0
            self.canvas.set(x, 0, c,
                flags = flg |
                    (canvas.NEGATIVE if i == self.cursor and self.focused else 0))

    @property
    def cursor(self):
        return self._cursor

    @cursor.setter
    def cursor(self, c):
        self._cursor = c
        self.update()

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, o):
        self._offset = o if o >= 0 else 0
        self.update()

    @property
    def size(self):
        return (self.length + 1, 1)

    def __str__(self):
        return "<%s.%s zindex = %d focused = %r focusable = %r size = %r " \
                "value = \"%s\">" % \
                (self.__class__.__module__, self.__class__.__name__,
                        self.zindex, self.focused, self.focusable, self.size,
                        self.value)


class Decade(ValueWidget):

    def __init__(self, digits, decimals = 0, value = 0, cursor = 0, max = None,
            min = None, onvalue = None):
        super(Decade, self).__init__(onvalue = onvalue)
        self.digits = digits
        self.decimals = decimals
        self.value = value
        self.cursor = cursor
        self.vstretch = False
        self.max = max if max is not None else 10 ** (self.digits - self.decimals) \
                - 10 ** (-self.decimals)
        self.min = min if min is not None else -10 ** (self.digits - self.decimals) \
                + 10 ** (-self.decimals)
        self._cannegative = self.min < 0

    @event.handler("key", key = "<right>")
    def _onright(self, kc):
        if self.cursor > 0:
            self.cursor -= 1

    @event.handler("key", key = "<left>")
    def _onleft(self, kc):
        if self.cursor < self.digits - 1:
            self.cursor += 1

    def _delta(self):
        return 10 ** (self.cursor - self.decimals)

    @event.handler("key", key = "+")
    def _add(self, kc):
        if self.value + self._delta() <= self.max:
            self.value += self._delta()
        else:
            self.value = self.max

    @event.handler("key", key = "-")
    def _sub(self, kc):
        if self.value - self._delta() >= self.min:
            self.value -= self._delta()
        else:
            self.value = self.min

    def render(self):
        self.canvas.clear()
        ox = int(self.canvas.width / 2 - self.size[0] / 2)
        sflags = canvas.BOLD if self.focused else 0
        if self._cannegative:
            self.canvas.set(ox, 0, "-" if self.value < 0 else " ", flags = sflags)
            ox += 1
        val = abs(round(self.value * 10 ** self.decimals))
        for i in range(self.digits):
            flags = sflags
            if i == self.digits - self.decimals:
                self.canvas.set(ox, 0, ".", flags = flags)
                ox += 1
            if i == self.digits - self.cursor - 1:
                flags = canvas.NEGATIVE
            self.canvas.set(ox, 0, "%d" % (val / (10 ** (self.digits - i - 1)) % 10),
                    flags = flags)
            ox += 1

    @property
    def cursor(self):
        return self._cursor

    @cursor.setter
    def cursor(self, c):
        self._cursor = c
        self.update()

    @property
    def size(self):
        return (self.digits + (1 if self.decimals else 0) + (1 if self._cannegative else 0), 1)


class Console(Widget):

    def __init__(self, minheight = 8, history = 200):
        super(Console, self).__init__()
        # TODO: Should this have input support?
        self.minheight = minheight
        self.history = history
        self._lines = collections.deque(maxlen = self.history)
        self._splitlines = collections.deque(maxlen = self.minheight)
        self.focusable = False

    def push(self, line):
        self._lines.appendleft(line)
        self._update_splitlines()
        self.update()

    def recalc(self):
        self._update_splitlines()

    def _update_splitlines(self):
        self._splitlines = []
        for line in self._lines:
            rem = len(line) % self.canvas.width
            self._splitlines.append(line[-rem:])
            for x in range(len(line) - rem, 0, -self.canvas.width):
                self._splitlines.append(line[x - self.canvas.width:x])


    def render(self):
        for y, l in zip(range(self.canvas.height - 1, -1, -1), self._splitlines):
            self.canvas.text(0, y, l + " " * (self.canvas.width - len(l)))

    @property
    def size(self):
        return (1, self.minheight)


class Checkbox(ValueWidget):

    def __init__(self, label = None, checked = False, onvalue = None):
        super(Checkbox, self).__init__(value = checked, onvalue = onvalue)
        self.label = label
        self.vstretch = False

    @event.handler("click")
    @event.handler("key", keys = [" ", "\r"])
    def _change(self, _):
        self.value = not self.value

    def render(self):
        s = "[✓]" if self.value else "[ ]"
        if self.label:
            s += " " + self.label + " "
        x = int(self.canvas.width / 2 - len(s) / 2)
        self.canvas.text(x, 0, s,
                flags = canvas.NEGATIVE if self.focused else 0)

    @property
    def size(self):
        return (3 + ((len(self.label) + 2) if self.label else 0), 1)


class Radio(ValueWidget):

    class Group(event.EventSource, list):

        def __init__(self, onvalue = None):
            super(Radio.Group, self).__init__()
            if onvalue:
                self.bind("value", onvalue)

        @property
        def selected(self):
            for m in self:
                if m.value:
                    return m
            return None

        def select(self, radio):
            old = self.selected
            for c in self:
                if c != radio:
                    c.value = False
                elif not c.value:
                    c.value = True
            if self.selected == old:
                return
            self.fire(event.ValueEvent(self.selected, old = old, source = self))

    def __init__(self, label = "", checked = False, group = None):
        super(Radio, self).__init__(value = checked)
        self.label = label
        self.vstretch = False
        self._group = None
        self.group = group

    @event.handler("value", new = True)
    def _onchange(self, ve):
        if self.group:
            self.group.select(self)

    @event.handler("click")
    @event.handler("key", keys = [" ", "\r"])
    def _set(self, _):
        self.value = True

    def _tick(self):
        return "(✓)" if self.value else "( )"

    def render(self):
        s = self._tick()
        if self.label:
            s += " " + self.label
        x = int(self.canvas.width / 2 - len(s) / 2)
        self.canvas.text(int(self.canvas.width / 2 - len(s) / 2), 0, s,
                flags = canvas.NEGATIVE if self.focused else 0)

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, gr):
        if self.group is not None:
            self.group.remove(self)
        self._group = gr
        if self.group is not None:
            self.group.append(self)

    @property
    def size(self):
        return (len(self._tick()) + (len(self.label) + 1) if self.label else 0, 1)
