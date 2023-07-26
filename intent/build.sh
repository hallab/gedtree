#!/bin/sh

. /home/hakan/src/kivy/pygame-android-kivy/kivy/environment.sh
export PGS4A_ROOT=/home/hakan/src/kivy/pygame-android-kivy/kivy/

cython intent.pyx
/home/hakan/src/kivy/pygame-android-kivy/kivy/python-install/bin/python.host setup.py build_ext -i
cp intent.so ..
