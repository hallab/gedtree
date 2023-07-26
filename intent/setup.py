from distutils.core import setup, Extension
import os

setup(name='intent',
      version='0.1',
      ext_modules=[

        Extension(
            'intent', ['intent.c', 'intent_jni.c'],
            libraries=[ 'sdl', 'log' ],
            library_dirs=[os.environ['PGS4A_ROOT'] + '/libs/'+os.environ['ARCH'] ],
            ),
        ]
      )
