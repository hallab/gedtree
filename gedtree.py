import kivy
kivy.require('1.0.5')

from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.treeview import TreeViewLabel
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import NumericProperty, BooleanProperty, ObjectProperty, \
                            ReferenceListProperty, StringProperty
from kivy.factory import Factory
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.config import Config
from kivy.base import stopTouchApp

import os, random, codecs

popup_history = []

class FullScreenScatter(Scatter):
    def __init__(self, **kwargs):
       super(FullScreenScatter, self).__init__(**kwargs)
       self.ease_in = False
       self.trigger = Clock.create_trigger(self.keep_on_screen, -1)
       self.bind(on_touch_up=self.trigger, 
                 on_touch_down=self.down)
       

    def keep_on_screen(self, *args):
        updates = {}
        x = min(self.x, 0)
        y = min(self.y, 0)
        scale = max(self.scale, 1)
        top = max(self.top, self.parent.top)
        right = max(self.right, self.parent.right)

        if x != self.x:
            updates['x'] = x
        if y != self.y:
            updates['y'] = y
        #if scale != self.size:
        #    updates['scale'] = scale
        if right != self.right:
            updates['right'] = right
        if top != self.top:
            updates['top'] = top

        if updates:
            if not self.ease_in:
                updates['t'] = 'out_bounce'
                updates['duration'] = 0.5
            else:
                updates['t'] = 'linear'
                updates['duration'] = 1
            Animation(**updates).start(self)
        self.ease_in = False

    def ease_in_next(self):
        self.ease_in = True

    def down(self, *args):
        self.ease_in = False
            

Factory.register('FullScreenScatter', module=__name__)

class InfiniteScatter(Scatter):
    def __init__(self, **kwargs):
       super(InfiniteScatter, self).__init__(**kwargs)
       self.scaled = True

    def collide_point(self, x, y):
        return True

    def trigger(self):
        pass

    def on_touch_down(self, touch):
        touch.double_tap_dispatched = False
        Scatter.on_touch_down(self, touch)

        if touch.is_double_tap and not touch.double_tap_dispatched:
            if not self.scaled:
                x, y = self.to_widget(touch.x, touch.y)
                Animation(scale=1.0, pos=(self.parent.width/2 - x,
                                          self.parent.height/2 - y),
                          t='linear', duration=0.25).start(self)
                self.scaled = True
            else:
                self.zoom_out()

    def zoom_out(self):
        s = min(float(self.parent.size[0])/self.size[0],
                float(self.parent.size[1])/self.size[1],
                1)
        anim = Animation(scale=s, center=self.parent.center,
                         t='linear', duration=0.25)
        anim.bind(on_complete=self.clear_scaled)
        anim.start(self)
                

    def on_scale(self, *args):
        self.scaled = True

    def on_size(self, *args):
        self.scaled = True
        
    def clear_scaled(self, *args):
        self.scaled = False

Factory.register('InfiniteScatter', module=__name__)


class NodeLabel(Label):
    column = ObjectProperty(None)
    touched = BooleanProperty(False)
    ged_node = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(NodeLabel, self).__init__(**kwargs)
        self.register_event_type('on_tapped')
        self.register_event_type('on_double_tapped')
        self.register_event_type('on_long_tapped')

    def on_touch_down(self, touch):
        x, y = touch.x, touch.y
        if not self.collide_point(x, y):
            return False

        if touch.is_double_tap:
            self.tapped = False            
            self.dispatch('on_double_tapped')
            touch.double_tap_dispatched = True

        touch.grab(self)
        self.touched = True
        timeout = 2*int(Config.get('postproc', 'double_tap_time'))/1000.0
        Clock.schedule_once(self.dispatch_long_tapped, timeout + 0.001)        
        return False

    def on_touch_move(self, touch):
        if not self.touched:
            return False
        x, y = touch.x, touch.y
        ox, oy = touch.ox, touch.oy
        d = (x-ox)**2 + (y-oy)**2
        if d > 20**2:
            self.touched = False
        return False

    def on_touch_up(self, touch):
        if not self.touched:
            return False
        self.touched = False
        Clock.unschedule(self.dispatch_long_tapped)
        touch.ungrab(self)
        
        if not touch.is_double_tap:
            self.tapped = True
            timeout = int(Config.get('postproc', 'double_tap_time'))/1000.0
            Clock.schedule_once(self.dispatch_tapped, timeout + 0.001)
        return True

    def dispatch_tapped(self, *args):
        if self.tapped:
            self.dispatch('on_tapped')
            
    def dispatch_long_tapped(self, *args):
        if self.touched:
            self.touched = False
            self.dispatch('on_long_tapped')

    def on_tapped(self):
        pass

    def on_double_tapped(self):
        pass

    def on_long_tapped(self):
        pass


Factory.register('NodeLabel', module=__name__)

class Edge(Widget):
    node1 = ObjectProperty(None)
    node2 = ObjectProperty(None)

    def __init__(self, node1, node2):
        super(Edge, self).__init__(node1=node1, node2=node2)
            
    def make_bezier(self, *args):
        left, right = self.node1, self.node2
        if left.x > right.x:
            left, right = right, left
        if not left.column:
            return (0,0)
        start = (right.pos[0], right.center_y)
        stop = (left.pos[0] + left.column.width, left.center[1])
        mid1 = (0.25*stop[0] + 0.75*start[0], start[1])
        mid2 = (0.50*stop[0] + 0.50*start[0], start[1])
        mid3 = (0.50*stop[0] + 0.50*start[0], stop[1])
        mid4 = (0.75*stop[0] + 0.25*start[0], stop[1])
        extra = (left.pos[0] + left.texture_size[0], left.center[1])
        return start + mid1 + mid2 + mid3 + mid4 + stop + extra

class Column(list):
    def __new__(cls, init=()):
        self = list.__new__(cls)
        self.xpos = -1
        self.width = -1
        self.yoffset = 0
        self.extend(init)
        return self

class Node(object):
    def __init__(self, tree, ged_node, label=None, hide=False):
        self.tree = tree
        self.ged_node = ged_node
        if label is None:
            a, b = ged_node.name()
            name = a
            if b:
                name += '\n' + b
            else:
                name += '\n '
            if hide:
                name = '...'
            label = NodeLabel(text=name, color=(0,0,0,1))
            label.texture_update()
        self.label = label
        label.size = label.texture_size
        label.ged_node = ged_node
        
        self.ypos = -1

    def place(self, above=0):
        spacing = 20
        self.ypos = max(above, spacing)
        if self.below:
            colpos = self.below.ypos + self.below.height + spacing
            self.ypos = max(self.ypos, colpos)

        if self.preceding:
            child_height = sum([p.height for p in self.preceding])
            child_height += (len(self.preceding) - 1) * spacing
            sa = sum([p.place(self.ypos - child_height/2 + self.height/2)
                      for p in self.preceding])
            newpos = sa / len(self.preceding)
            assert newpos >= self.ypos
            self.ypos = newpos
        return self.ypos

    def apply(self):
        for p in self.preceding:
            p.apply()
        self.label.y = self.ypos

    @property
    def height(self):
        return self.label.texture_size[1]

    def setup_for_column(self, col):
        self.label.x = col.xpos
        self.label.column = col
        self.tree.add_widget(self.label)
        self.label.bind(on_double_tapped=self.tree.change_root,
                        on_long_tapped=self.tree.change_root,
                        on_tapped=self.tree.show_node_into)
        


class GedTree(Widget):
    base = ObjectProperty(None)
    xspacing = NumericProperty(50)
    yspacing = NumericProperty(20)

    vissible_width = NumericProperty(100)
    vissible_height = NumericProperty(100)
    vissible_size = ReferenceListProperty(vissible_width, vissible_height)
    maxdepth = None

    def __init__(self, **kwargs):
        super(GedTree, self).__init__(**kwargs)
        trigger = Clock.create_trigger(self.on_tree, 0)
        def call_on_tree(self, *args):
            self.parent.parent.busy = True
            trigger()
        self.bind(base=call_on_tree)
        self.tip = None
        Clock.schedule_once(self.show_tip, random.randrange(3*60)) # ONLY_IN_FREE_VERSION
        Clock.schedule_interval(self.show_tip, 5*60) # ONLY_IN_FREE_VERSION

    def show_tip(self, t=None):
        content = TipContent()
        if self.tip:
            self.tip.dismiss()
        self.tip = LightPopup(title='Tip',
                              content=content,
                              size_hint=(None, None), size=(400, 400),
                              )
        self.tip.open()
        
    def build_columns(self, method, base):
        if self.maxdepth is None:
            if self.parent.parent.config: 
                def cb(section, key, value):
                    self.maxdepth = int(value)
                    self.on_tree()
                self.parent.parent.config.add_callback(cb, 'GedTree', 'MaxDepth')
                self.maxdepth = int(self.parent.parent.config.get('GedTree', 'MaxDepth'))
            else:
                self.maxdepth = 10
        maxdepth = self.maxdepth + 1
        columns = [Column([base])]
        while columns[-1]:
            col = Column()
            prev = None
            for n in columns[-1]:
                if len(columns) <= maxdepth:
                    n.preceding = [Node(self, p, hide=(len(columns) >= maxdepth-1))
                                   for p in getattr(n.ged_node, method)() if p]
                else:
                    n.preceding = []
                col.extend(n.preceding)
                n.below = prev
                prev = n
            if len(columns) > maxdepth:
                break
            columns.append(col)
        columns.pop()
        return columns
        
    def on_tree(self, *args):
        if not self.base:
            return
        
        old_labels = {}
        for w in self.children:
            if isinstance(w, NodeLabel):
                old_labels[w.ged_node] = w

        if self.base in old_labels:
            old_base_pos = old_labels[self.base].pos
        else:
            old_base_pos = self.parent.parent.center
            
        self.clear_widgets()        

        parent_base = Node(self, self.base)
        parent_columns = self.build_columns('all_parents', parent_base)
        parent_columns.reverse()

        child_base = Node(self, self.base, parent_base.label)
        child_columns = self.build_columns('children', child_base)

        prev = None
        for col in parent_columns + child_columns[1:]:
            if prev:
                col.xpos = prev.xpos + prev.width + self.xspacing
            else:
                col.xpos = 20
            for n in col:
                n.setup_for_column(col)
                for p in n.preceding:
                    self.add_widget(Edge(p.label, n.label))
                    
            col.width = max([n.label.texture_size[0] for n in col])
            prev = col

        for p in child_base.preceding:
            self.add_widget(Edge(p.label, child_base.label))
            
        parent_base.place()
        child_base.place()

        if parent_base.ypos > child_base.ypos:
            dy = parent_base.ypos - child_base.ypos
            columns = child_columns
        elif parent_base.ypos < child_base.ypos:
            dy = child_base.ypos - parent_base.ypos
            columns = parent_columns
        else:
            columns = []
        for col in columns:
            for n in col:
                n.ypos += dy
        
        parent_base.apply()
        child_base.apply()

        self.resize()

        l = child_base.label
        cx, cy = l.to_window(*l.pos)
        ox, oy = l.to_window(*old_base_pos)

        #self.parent.ease_in_next()
        self.parent.x += ox - cx
        self.parent.y += oy - cy
        self.parent.trigger()
        if self.parent.parent.zoom_out_needed:
            self.parent.parent.zoom_out_needed = False
            self.parent.zoom_out()
            
        self.parent.parent.busy = False
            

    def resize(self):

        tree_width = max([w.right + 20 for w in self.children
                          if isinstance(w, NodeLabel)])
        tree_height = max([w.top + 20 for w in self.children
                           if isinstance(w, NodeLabel)])
        self.size = (tree_width, tree_height)
        return

        width = max(tree_width, self.vissible_width)
        height = max(tree_height, self.vissible_height)
        aspect = float(width) / height
        vissible_aspect = float(self.vissible_width) / self.vissible_height
        if aspect < vissible_aspect:
            scale = float(self.vissible_height) / height
            width = float(self.vissible_width) / scale
        else:
            scale = float(self.vissible_width)/width
            height = float(self.vissible_height) / scale            

        dx = (width - tree_width) / 2
        dy = (height - tree_height) / 2
        for w in self.children:
            w.x += dx
            w.y += dy
        
        self.parent.scale_min = scale
        if self.parent.scale < scale:
            self.parent.scale = scale
        self.size = (width, height)

    def change_root(self, node):
        self.base = node.ged_node

    def show_node_into(self, node):
        content = ShowNodeContent()

        name = ' '.join(node.ged_node.name())
        s = node.ged_node.sex()
        if s == 'M':
            name += ' (male)'
        elif s == 'F':
            name += ' (female)'
        
        txt = ''
        b = node.ged_node.birth()
        if b:
            txt += 'Born '
            if b.date:
                txt += b.date
            if b.place:
                txt += ' in ' + b.place

        for f in node.ged_node.families():
            if f.husband() is node.ged_node:
                partner = f.wife()
            elif f.wife() is node.ged_node:
                partner = f.husband()
            else:
                continue
            for m in f.marriage_events:
                txt += '\n'
                m = f.marriage()
                txt += 'Married ' + ' '.join(partner.name())
                if m.date:
                    txt += ' ' + m.date
                if m.place:
                    txt += ' in ' + m.place

        d = node.ged_node.death()
        if d:
            txt += '\n'
            txt += 'Died '
            if d.date:
                txt += d.date
            if d.place:
                txt += ' in ' + d.place

        txt += '\n\n'
        for note in node.ged_node.notes():
            txt += '\n\n' + note.text()
        
        content.text = txt

        w, h = self.get_root_window().size
        w -= 100
        h -= 100
        w = min(w, h)

        popup = LightPopup(title=name,
                      content=content,
                      size_hint=(None, None), size=(w, h),
                      )        
        popup.open()
        

Factory.register('GedTree', module=__name__)

    
class GedTreeView(Widget):
    busy = BooleanProperty(False)    
    base = ObjectProperty(None)
    zoom_out_needed = True
    
    def __init__(self, config=None, **kwargs):
        Widget.__init__(self, **kwargs)
        self.config = config

    def back(self):
        if popup_history:
            popup_history[-1].back()
        else:
            stopTouchApp()
            

class LightButton(Button):
    def __init__(self, *args, **kwargs):
        Button.__init__(self, *args, **kwargs)
        self.color = 0,0,0,1
        self.background_normal = 'button.png'
        self.background_down = 'button_pressed.png'
        self.border = 3,3,3,3
        
Factory.register('LightButton', module=__name__)

class LightPopup(Popup):
    def __init__(self, *args, **kwargs):
        Popup.__init__(self, *args, **kwargs)
        self.background = 'menu-background.png'
        self.children[0].children[-1].color = 0,0,0,1

        def register(*args):
            popup_history.append(self)
        def unregister(*args):
            try:
                popup_history.remove(self)
            except ValueError:
                pass
        self.bind(on_open=register)
        self.bind(on_dismiss=unregister)
        
    def back(self):
        self.dismiss()


class PopupMenu(BoxLayout):

    app = ObjectProperty(None)
    
    def __init__(self, window, **kwargs):
        BoxLayout.__init__(self, **kwargs)
        self._window = window
        self.center_x = window.center[0]
        self.top = 0

    def open(self):
        self._window.add_widget(self)
        Animation(top=self.height, t='out_circ', duration=0.25).start(self)
        popup_history.append(self)
        
    def close(self):
        anim = Animation(top=0, t='out_circ', duration=0.25)
        anim.bind(on_complete=self._remove)
        anim.start(self)
        try:
            popup_history.remove(self)
        except ValueError:
            pass
    
    def back(self):
        self.close()

    def _remove(self, *args):
        self._window.remove_widget(self)
        
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            self.close()
            return True
        BoxLayout.on_touch_down(self, touch)

Factory.register('PopupMenu', module=__name__)

class OpenGedContent(BoxLayout):
    files = ObjectProperty(None)
    scroll = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        BoxLayout.__init__(self, **kwargs)
        self.topdirs = [
            ('/mnt/sdcard/Download',
             TreeViewLabel(text='Downloads', color=(0,0,0,1))),
            ('/mnt/sdcard/Android/data/com.dropbox.android/files/scratch',
             TreeViewLabel(text='Dropbox', color=(0,0,0,1))),
            ('/mnt/sdcard',
             TreeViewLabel(text='SDCard', color=(0,0,0,1))),
            ('/',
             TreeViewLabel(text='Root', color=(0,0,0,1))),
            ]
        for d in self.topdirs:
            d[1].listed = False
            d[1].full_path = d[0]
            self.files.add_node(d[1])
            d[1].bind(on_touch_down=self.node_selected)
        self.keep_top_at = None
        self.files.bind(top=self.new_position)

    def node_selected(self, node, touch=None):
        if os.path.isdir(node.full_path):
            if not node.listed:
                node.listed = True
                files = []
                try:
                    for f in os.listdir(node.full_path):
                        fn = os.path.join(node.full_path, f)
                        if os.path.isdir(fn) or fn.lower().endswith('.ged'):
                            files.append(f)
                except OSError:
                    pass
                files.sort()
                if not files:
                    files.append('(no .ged files found)')
                for f in files:
                    fn = os.path.join(node.full_path, f)
                    n = TreeViewLabel(text=f, color=(0,0,0,1))
                    n.full_path = fn
                    n.listed = False
                    n.bind(on_touch_down=self.node_selected)
                    self.files.add_node(n, node)
            self.keep_top_at = self.files.top
            self.files.toggle_node(node)
                    

    def open_ged(self, *args):
        n = self.files.selected_node
        if not n:
            return
        if n.full_path.lower().endswith('.ged'):
            self.app.open_ged(n.full_path)
            self.popup.dismiss()
        elif os.path.isdir(n.full_path):
            self.node_selected(n)

    def new_position(self, node, *args):
        if self.keep_top_at:
            dy = self.keep_top_at - self.files.top
            self.keep_top_at = None
            sx, sy = self.scroll.convert_distance_to_scroll(0, dy)
            self.scroll.scroll_y -= sy

class ShowNodeContent(BoxLayout):
    text = StringProperty('')

class MessageContent(BoxLayout):
    text = StringProperty('')
    
class TipContent(BoxLayout):
    def tip(self):
        return random.choice([
            'Drag the view to scroll around.',
            'Pinch with two fingers to zoom in or out.',
            'Double tap on background to zoom in or out.',
            'Single tap on a name to show more info.',
            'Double tap on a name to base the tree on that person.',
            'Long tap on a name to base the tree on that person.',
            'The full version does not have these annoying tips.',
            'Mail a .ged file to yourself and download it\nto your tablet. Click on it in the Downloads\napps or in the file browser.',
            'Use the Dropbox app to keep your .ged files\nsyncornized on all your devices.',
            'You can tune the number of generations to be\nshown simultaneously from the Configure menu.',
            ])
        
    
    def view(self, url):
        from android import open_url
        open_url(url)

if __name__ == '__main__':
    from main import GedTreeApp
    GedTreeApp().run()
