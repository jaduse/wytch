#! /usr/bin/env python3
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

from wytch import builder, colors, view, canvas, event, Wytch

w = Wytch()

class ColorButton(view.Widget):

    def __init__(self, color, board):
        super(ColorButton, self).__init__()
        self.color = color
        self.board = board
        self.focusable = False
        self.hstretch = False
        self.vstretch = False

    @event.handler("mouse", pressed = True)
    def _onmouse(self, me):
        self.board.colors[me.button] = self.color

    def render(self):
        self.canvas.square(0, 0, self.canvas.width, self.canvas.height,
                           self.color)

    @property
    def size(self):
        return (5, 2)

class DrawingBoard(view.Widget):

    def __init__(self):
        super(DrawingBoard, self).__init__()
        self.grid = None
        self.oldme = None
        self.colors = {}
        self._buffer = None

    @event.handler("key", key = "c")
    def _onclear(self, kc):
        self._buffer.clear()
        self.update()

    @event.handler("mouse")
    def _onmouse(self, me):
        if me.released:
            if self.oldme:
                key = self.oldme.button
            else:
                return
        else:
            key = me.button
        color = self.colors.get(key, colors.DARKGREEN)
        if not self.oldme:
            self._buffer.set(me.x, me.y, " ", bg = color)
        else:
            self._buffer.line(self.oldme.x, self.oldme.y, me.x, me.y, bg = color)

        if me.released:
            self.oldme = None
        else:
            self.oldme = me
        self.update()

    def recalc(self):
        if not self._buffer or self._buffer.width != self.canvas.width \
                or self._buffer.height != self.canvas.height:
            self._buffer = canvas.BufferCanvas(self.canvas)

    def render(self):
        self._buffer.flush()

    @property
    def size(self):
        return (1, 1)

with w:
    board = DrawingBoard()
    w.root.bind("key", lambda _: w.exit(), key = "q")
    with builder.Builder(w.root) as b:
        h = b.vertical() \
            .horizontal()
        for c in colors.c256[:16]:
            h.add(ColorButton(c, board))
        h.end().add(board)
