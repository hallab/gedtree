# Vibration support.
cdef extern void intent_vibrate(double)
cdef extern void intent_view(char * uri)
cdef extern char *intent_filename()

def vibrate(s):
    intent_vibrate(s)

def view(uri):
    intent_view(uri)
    
def filename():
    return intent_filename()
    
