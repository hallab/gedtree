import sys
sys.argv = ['test']

from kivy.base import runTouchApp, stopTouchApp, EventLoop
from kivy.input.providers.mouse import MouseMotionEvent
from kivy.graphics import Color, Rectangle
from simplepyged.gedcom import Gedcom
from gedtree import *
import ansel

from kivy.lang import Builder
Builder.load_file('gedtree.kv')

import time, itertools, random, pytest

if pytest.config.getvalue('kivy_noanim'):
    from kivy.animation import Animation
    original_initialize = Animation._initialize
    def initialize(self, widget):
        original_initialize(self, widget)
        self._widgets[widget]['time'] = float('Inf')
    Animation._initialize = initialize


class Fake(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class FakeTouch(object):
    def __init__(self, sx, sy, button='left', id='mouse1'):
        self.touch = MouseMotionEvent('mouse', id, [sx, sy, button])

    def down(self):
        EventLoop.post_dispatch_input('begin', self.touch)

    def move(self, sx, sy):
        self.touch.move([sx, sy, self.touch.button])
        EventLoop.post_dispatch_input('update', self.touch)
        
    def up(self):
        EventLoop.post_dispatch_input('end', self.touch)        
    
class EventTest(object):
    _running = False
    default_runframes = 2
    default_runtime = 0
    if not pytest.config.getvalue('kivy_noanim'):
        default_runtime = 1
    max_rendering_time = 0.25
    
    def start(self, root, runframes=None, runtime=None, check=True):
        if self._running:
            self.stop()
        self._running = True
        self.root = root
        
        from os import environ
        environ['KIVY_USE_DEFAULTCONFIG'] = '1'

        # force window size + remove all inputs
        from kivy.config import Config
        Config.set('graphics', 'width', '800')
        Config.set('graphics', 'height', '600')
        if not pytest.config.getvalue('kivy_record'):
            for items in Config.items('input'):
                Config.remove_option('input', items[0])
            
        
        # bind ourself for the later screenshot
        from kivy.core.window import Window
        Window.bind(on_flip=self.on_window_flip)

        # ensure our window is correcly created
        Window.create_window()

        from kivy.base import runTouchApp
        runTouchApp(root, slave=True)

        self._framecount = 0

        EventLoop.window.dispatch('on_resize', *EventLoop.window.size)
        self.run(runframes, runtime)

    def on_window_flip(self, window):
        self._framecount += 1
        self._last_frame_rendered = time.time()

    def run(self, runframes=None, runtime=None, check=True):
        if runframes is None:
            runframes = self.default_runframes
        if runtime is None:
            runtime = self.default_runtime
        assert self._running
        start_time = time.time()
        start_frame = self._framecount

        while (self._framecount < start_frame + runframes or 
               time.time() < start_time + runtime):
            EventLoop.window._mainloop()
            timeout = self._last_frame_rendered + self.max_rendering_time
            if time.time() > timeout:
                break

        if check:
            self.assert_invariants()

    def assert_invariants(self):
        pass

    def stop(self):
        if not self._running:
            return
        if pytest.config.getvalue('kivy_record'):
            self._record()
        
        from kivy.core.window import Window
        Window.remove_widget(self.root)
        self.root = None
        stopTouchApp()
        EventLoop.stop()
        self._running = False

    def teardown_method(self, method):
        self.stop()

    def _record(self):
        self.root.bind(on_touch_down=self.log_touch_down,
                       on_touch_move=self.log_touch_move,
                       on_touch_up=self.log_touch_up)
        while True:
            self.run(runtime=float('Inf'))

    def log_touch(self, widget, touch, event):
        #print '%s(x=%d, y=%d, ox=%d, oy=%d)' % (event, touch.x, touch.y,
        #                                        touch.ox, touch.oy)
        print '%s(device=%r, id=%r, sx=%.4f, sy=%.4f, button=%r)' % (
            event, touch.device, touch.id, touch.sx, touch.sy, touch.button)

    def log_touch_down(self, widget, touch):
        print touch
        self.log_touch(widget, touch, 'on_touch_down')

    def log_touch_move(self, widget, touch):
        self.log_touch(widget, touch, 'on_touch_move')

    def log_touch_up(self, widget, touch):
        self.log_touch(widget, touch, 'on_touch_up')


    def tap(self, sx, sy):
        touch = FakeTouch(sx, sy)
        touch.down()
        touch.up()
        self.run()
        
    def double_tap(self, sx, sy):
        touch = FakeTouch(sx, sy)
        touch.down()
        touch.up()
        touch.touch.is_double_tap = True
        touch.down()
        touch.up()
        self.run()

    #def swipe(self, sx0, sy0, sx1, sy1, prerun=None):
    def swipe(self, *args, **kwargs):
        if args:
            assert 'a' not in kwargs
            kwargs['a'] = args

        touches = []
        for t in 'abcdefghijklmnopqrstuvwxyz':
            if t in kwargs:
                sx0, sy0, sx1, sy1 = kwargs[t]
                touches.append(FakeTouch(sx0, sy0))
                touches[-1]._end = sx1, sy1
                touches[-1].down()

        for touch in touches:
            touch.move(*touch._end)
        for touch in touches:
            touch.up()

        if 'prerun' in kwargs:
            kwargs['prerun']()
        self.run()
        
    # FIXME: Add between events but dont hang if frame is not redrawn
        
    def widgets(self, kind=None):
        worklist = [self.root]
        while worklist:
            w = worklist.pop()
            if kind is None or isinstance(w, kind):
                yield w
            worklist += w.children

    def fully_vissible(self, widget):
        x0, y0 = widget.to_window(*widget.pos)
        right, top  = widget.to_window(widget.right, widget.top)
        for x, y in itertools.product([x0, right], [y0, top]):
            if not self.root.collide_point(x, y):
                return False
        return True

    def center_vissible(self, widget):
        return self.root.collide_point(*widget.to_window(*widget.center))

    def random_tap(self, kind=Widget):
        centers = [n.center for n in self.widgets(kind)
                   if self.root.collide_point(*n.to_window(*n.center))]
        if not centers:
            return
        center = random.choice(centers)
        self.tap(center[0] / self.root.width,
                 center[1] / self.root.height)
        
    def random_double_tap(self, kind=Widget):
        centers = [n.center for n in self.widgets(kind)
                   if self.root.collide_point(*n.to_window(*n.center))]
        if not centers:
            return
        center = random.choice(centers)
        self.double_tap(center[0] / self.root.width,
                 center[1] / self.root.height)
        
    def random_swipe(self, fingers=(1,)):
        n = random.choice(fingers)
        kwargs = {}
        for i in range(n):
            swipe = [random.random() for j in range(4)]
            kwargs['abcdefghijklmnopqrstuvwxyz'[i]] = swipe
        self.swipe(**kwargs)

    def random_run(self, events, n=100):
        seed = int(time.time()*1000)
        print 'random_run seed: ', seed
        random.seed(seed)
        for i in range(n):
            random.choice(events)()
        

class TestFullScreenScatter(EventTest):
    
    def start(self, w, h):    
        root = Widget()
        scatter = FullScreenScatter()
        scatter.size = (w, h)
        scatter.scale_min = 1 # For now
        scatter.do_rotation = False # For now
        root.add_widget(scatter)
        label = Label(text='Hello')
        label.size = (w, h)
        with label.canvas.before:
            Color(1., 0, 0)
            Rectangle(pos=label.pos, size=label.size)
        scatter.add_widget(label)
        self.label = label
        EventTest.start(self, root)

    def assert_invariants(self):
        x, y = self.label.to_window(*self.label.pos)
        right, top  = self.label.to_window(self.label.right, self.label.top)
        w, h = self.root.size
        assert (x <= 0 and right >= w) or abs(x - (w-right)) < 3
        assert (y <= 0 and top >= h) or abs(y - (h-top)) < 3

    def assert_moved(self):
        assert self.label.to_window(*self.label.pos) != (0, 0)
        
    def test_basic(self):
        self.start(800, 600)
        
        self.swipe(0.4288, 0.2100, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.4288, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.2100, 0.6837, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)

        self.swipe(0.4288, 0.2100, 0.6837, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.4288, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.2100, 0.4288, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.4288, 0.5617, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)

    def test_too_high(self):
        self.start(800, 700)
        
        self.swipe(0.4288, 0.2100, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.4288, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.2100, 0.6837, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, -100)

        self.swipe(0.4288, 0.2100, 0.6837, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.4288, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, -100)
        self.swipe(0.6837, 0.2100, 0.4288, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.4288, 0.5617, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, -100)

    def test_too_wide(self):
        self.start(900, 600)
        
        self.swipe(0.4288, 0.2100, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.4288, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, 0)
        self.swipe(0.6837, 0.2100, 0.6837, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, 0)
        self.swipe(0.6837, 0.5617, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, 0)

        self.swipe(0.4288, 0.2100, 0.6837, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.4288, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, 0)
        self.swipe(0.6837, 0.2100, 0.4288, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, 0)
        self.swipe(0.4288, 0.5617, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)

    def test_too_big(self):
        self.start(900, 700)
        
        self.swipe(0.4288, 0.2100, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.4288, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, 0)
        self.swipe(0.6837, 0.2100, 0.6837, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, 0)
        self.swipe(0.6837, 0.5617, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, -100)

        self.swipe(0.4288, 0.2100, 0.6837, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, 0)
        self.swipe(0.6837, 0.5617, 0.4288, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, -100)
        self.swipe(0.6837, 0.2100, 0.4288, 0.5617, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (-100, 0)
        self.swipe(0.4288, 0.5617, 0.6837, 0.2100, prerun=self.assert_moved)
        assert self.label.to_window(*self.label.pos) == (0, -100)

    def test_scale(self):
        self.start(800, 600)
        self.swipe(a=(0.4, 0.4, 0.1, 0.1),
                   b=(0.6, 0.6, 0.9, 0.9))
        x, y = self.label.to_window(*self.label.pos)
        right, top  = self.label.to_window(self.label.right, self.label.top)
        assert right - x  == 3200
        assert top - y == 2400
        assert not self.fully_vissible(self.label)
        assert self.center_vissible(self.label)
        self.swipe(0.9, 0.9, 0.1, 0.1)
        assert not self.fully_vissible(self.label)        
        assert not self.center_vissible(self.label)

    def test_random(self):
        self.start(800, 600)
        self.random_run([lambda: self.random_swipe([1, 2])])

    # too small, random
    # scaling
    # scale into too small
    # rotations
    # kill scatter.scale_min and scatter.do_rotation
    
    # def test_pos_prior_to_release
    # def test_used_as_top_widget

    # without animations parameter

class FakeParentsOnlyNode(object):
    def __init__(self, num):
        self.num = num
        self._parents = []
        self._children = []        
        if self.num < 10:
            self._parents = [FakeParentsOnlyNode(self.num + i)
                             for i in range(1, 3)]

    def name(self):
        return str(self.num)*5, str(self.num)*8

    def parents(self):
        return self._parents

    def all_parents(self):
        return self._parents

    def children(self):
        return self._children

class FakeNode(FakeParentsOnlyNode):
    def __init__(self, num):
        self.num = num
        self._parents = []
        self._children = []
        if self.num < 10:
            self._parents = [FakeNode(self.num + i)
                             for i in range(1, 3)]
        for p in self._parents:
            p._children.append(self)

    def make_childs(self, other, n):
        for i in range(n):
            n = FakeNode(i + 10)
            n._parents = [self, other]
            self._children.append(n)
            other._children.append(n)


class TestGedTreeView(EventTest):
    def start(self, node):
        self._tree = None
        EventTest.start(self, GedTreeView(base=node))

    @property
    def tree(self):
        if not self._tree:
            widgets = list(self.widgets(GedTree))
            assert len(widgets) == 1
            self._tree = widgets[0]
        return self._tree

    @property
    def nodes(self):
        for w in self.widgets(NodeLabel):
            yield w
            
    def assert_centered(self):
        a = min(n.x for n in self.nodes)
        b = min(self.tree.width - n.right for n in self.nodes)
        assert abs(a - b) < 3
        a = min(n.y for n in self.nodes)
        b = min(self.tree.height - n.top for n in self.nodes)
        assert abs(a - b) < 3

        #assert self.tree.width >= self.root.width
        #assert self.tree.height >= self.root.height

    def assert_no_overlaps(self):
        for n1, n2 in itertools.combinations(self.nodes, 2):
            assert not n1.collide_widget(n2)

    def assert_node_vissible(self):
        for n in self.nodes:
            if self.root.collide_point(*n.to_window(*n.pos)):
                break
        else:
            assert False
        
    def assert_invariants(self):
        self.assert_centered()
        self.assert_no_overlaps()
        #self.assert_node_vissible() FIXME: for now
        # FIXME: assert vertical alignment to parents/childs
        
    def zoom_out(self):
        self.root.children[0].zoom_out()
        self.run()
        
    def test_parents_small(self):
        self.start(FakeParentsOnlyNode(7))
        assert len(list(self.nodes)) == 9
        self.double_tap(0.4213, 0.3900)
        assert len(list(self.nodes)) == 3
        self.double_tap(0.21, 0.3400)
        assert len(list(self.nodes)) == 1
        self.double_tap(0.5, 0.5)
        assert len(list(self.nodes)) == 1

    def test_small(self):
        self.start(FakeNode(7))
        assert len(list(self.nodes)) == 9
        self.double_tap(sx=0.6488, sy=0.4233)
        assert len(list(self.nodes)) == 6
        self.zoom_out()
        self.double_tap(sx=0.2275, sy=0.5250)
        assert len(list(self.nodes)) == 4
        self.zoom_out()
        self.double_tap(sx=0.7600, sy=0.4500)
        assert len(list(self.nodes)) == 4

    def test_multiple_childs(self):
        node = FakeNode(7)
        node._parents[0].make_childs(node._parents[1], 2)
        n = node._parents[0]._parents[0]
        n._parents[0].make_childs(n._parents[1], 1)
        self.start(node)
        assert len(list(self.nodes)) == 9        
        self.double_tap(sx=0.6512, sy=0.4183)
        assert len(list(self.nodes)) == 8
        self.zoom_out()
        self.double_tap(sx=0.1375, sy=0.5033)
        assert len(list(self.nodes)) == 7

    some_geds = ['testgeds/' + f for f in os.listdir('testgeds') if os.path.isfile('testgeds/' + f)]
    some_geds += ['testgeds/somedir/AnnaGreta.ged']
    latin1_geds = {'testgeds/Disnew.ged', 'testgeds/Dis.ged', 'testgeds/Bylander_latin1.ged',
                  'testgeds/Liten-16.GED', 'testgeds/Pearson.GED', 'testgeds/GOLD_2012-10-04.ged',
                  'testgeds/Hermansen.GED'}
    ansel_geds = {'testgeds/SHARPLES1.ged'}
    
    def test_random_full(self):
        def myswipe():
            self.random_swipe([1])
            if not pytest.config.getvalue('kivy_noanim'):
                self.run(0, 1)
            #print self.widgets(FullScreenScatter).next().scale
        self.start(Gedcom('testgeds/vka.ged').individual_list()[0])        
        self.random_run([lambda: self.random_double_tap(NodeLabel), myswipe], 100)

    def test_random_tapping(self):
        self.start(FakeNode(10))
        for fn in self.some_geds:
            self.tree.base = Gedcom(fn).individual_list()[0]
            self.tree.on_tree()
            self.random_run([lambda: self.random_double_tap(NodeLabel)], 100)

    def test_unbalanced(self):
        tree = FakeNode(9)
        tree.parents()[1]._parents.append(FakeNode(12))
        self.start(tree)
        
    def test_big(self):
        self.start(FakeNode(0))

    def test_load_geds(self):
        for fn in self.some_geds:
            print fn
            if fn in self.latin1_geds:
                codec = 'latin-1'
            elif fn in self.ansel_geds:
                codec = 'ansel'
            else:
                codec = 'utf-8'
            people = Gedcom(fn, (codec, None)).individual_list()
            assert len(people) > 0

