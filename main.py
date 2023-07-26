import kivy, os
kivy.require('1.0.5')

from gedtree import *
import sys, json
from simplepyged.gedcom import Gedcom
from simplepyged.matches import MatchList
from kivy.app import App
import traceback, codecs, ansel

def decode_error(error):
    GedTreeApp.codec_decoding_failed = True
    return codecs.lookup_error('replace')(error)
codecs.register_error('GedTreeAppError', decode_error)

class GedTreeApp(App):    
    last_ged_file = None
    
    def build(self):
        self._menu = None
        self.view = GedTreeView(self.config)
        self.load_on_resume = None

        self.bind(on_start = self.post_build_init) 
        
        return self.view
        
    def post_build_init(self,ev): 
        try:
            import android
        except ImportError:
            pass
        else:
            import pygame 
            import android.activity
            #android.map_key(android.KEYCODE_MENU, 1000) 
            android.map_key(android.KEYCODE_BACK, 1001) 
            #android.map_key(android.KEYCODE_HOME, 1002) 
            #android.map_key(android.KEYCODE_SEARCH, 1003) 
            android.activity.bind(on_new_intent=self.on_new_intent)
        win = self._app_window 
        win.bind(on_keyboard=self.key_handler)

        if len(sys.argv) > 1:
            self.open_ged(*sys.argv[1:])
        else:
            #self.open_ged('vka.ged', 'Ylva')
            fn = None
            try:
                fn = os.environ['PYTHON_OPENFILE']
            except KeyError:
                pass
            if not fn:
                try:
                    with open('last_ged_file') as f:
                        fn = f.read()
                except IOError:
                    pass
            if not fn:
                fn = 'example.ged'
            self.open_ged(fn)
        def cb(section, key, value):
            if self.last_ged_file:
                self.open_ged(self.last_ged_file)
        self.config.add_callback(cb, 'GedTree', 'Codec')
        
        
    def key_handler(self, window, key, scancode, unicode, modifier):
        if key == 1001 or key == 283:
            self.view.back()

    def open_ged(self, fn, name=None):
        GedTreeApp.codec_decoding_failed = False
        try:
            os.unlink('last_ged_file')
        except OSError:
            pass
        self.last_ged_file = fn
        try:
            people = Gedcom(fn, (self.config.get('GedTree', 'Codec'), 'GedTreeAppError')).individual_list()
        except Exception, e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            msg = MessageContent()
            msg.text = str(e) + '\n\n\nIt might help to adjust the Codec setting found by selecting Settings.. from the menu. Otherwise, please consider mailing the .ged ' + \
                       'file to hallabab@gmail.com for investigation.'
            popup = LightPopup(title="Open failed",
                               size_hint=(None, None), size=(300, 300),
                               content=msg)
            popup.open()
            return
        self.view.zoom_out_needed = True
        if name:
            matcher = MatchList(people)
            self.view.base = matcher.criteria_match('name=' + name)[0]
        else:
            self.view.base = people[0]
        with open('last_ged_file', 'w') as f:
            f.write(fn)
        if GedTreeApp.codec_decoding_failed and self.config.get('GedTree', 'CodecWarnings') == 'Yes':
            msg = MessageContent()
            msg.text = ('Your ged file is not in %s format. Please select Settings.. from the menu and' + 
                        ' change the Codec setting. If your codec is not listed, feel free to contact ' + 
                        'hallabab@gmail.com.') % self.config.get('GedTree', 'Codec')
            popup = LightPopup(title="Codec Error",
                               size_hint=(None, None), size=(300, 300),
                               content=msg)
            popup.open()



    def open_settings(self, *args):
        if not self._menu:
            self._menu = PopupMenu(self._app_window, app=self)
        self._menu.open()
        
    def open_settings_pannel(self):
        App.open_settings(self)

    def open_ged_popup(self):
        content = OpenGedContent()
        popup = LightPopup(title='Open ged file...',
                      content=content,
                      size_hint=(None, None), size=(400, 400),
                      )
        content.popup = popup
        content.app = self
        popup.open()

    def build_config(self, config):
        config.setdefaults('GedTree', {
            'MaxDepth': '5',
            'Codec': 'utf-8',
            'CodecWarnings': 'Yes',
            })

    def build_settings(self, settings):
        data = [

            { "type": "numeric",
              "title": "MaxDepth",
              "desc": "Number of generations shown.",
              "section": "GedTree",
              "key": "MaxDepth" },
            { "type": "options",
              "options": ['utf-8', 'ascii', 'latin_1', 'ansel'],
              "title": "Codec",
              "desc": "Codec used to encode strings in the ged files.",
              "section": "GedTree",
              "key": "Codec" },
            { "type": "options",
             "options": ['Yes', 'No'],
              "title": "Codec Warnings",
              "desc": "Warn on codec failuers.",
              "section": "GedTree",
              "key": "CodecWarnings" },
            

            
            ]
        settings.add_json_panel('GedTree',
                                self.config, data=json.dumps(data))


    def on_pause(self):
        return True

    def on_resume(self):
        if self.load_on_resume:
            self.open_ged(self.load_on_resume)
            self.load_on_resume = None


    def on_new_intent(self, intent):
        data = intent.getData()
        if data:
            path = data.getEncodedPath()
            if path:
                self.open_ged(path)



if __name__ in ('__android__', '__main__'):
    GedTreeApp().run()
    
