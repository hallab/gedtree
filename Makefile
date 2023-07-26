VERSION=0.9.14
FREE=Free
#BUILDDIR=../python-for-android/dist/default/
#BUILDDIR=../Kivy-1.0.9-android/
BUILDDIR=/usr/local/src/python-for-android/dist/default/
#BUILDARGS=--dir ~/src/kivy/gedtree/dist --package net.ardoe.hakan.gedtree`echo $(FREE) | tr F f` --icon ~/src/kivy/gedtree/tree-icon_128.png --orientation sensor --view-file-type ged --name "GedTree"$(FREE)
BUILDARGS=--dir $(shell pwd)/dist --package net.ardoe.hakan.gedtree`echo $(FREE) | tr F f` --icon $(shell pwd)/tree-icon_128.png --orientation sensor --name "GedTree"$(FREE) --intent-filters $(shell pwd)/intent-filter.xml
JAVA_HOME=/usr/lib/jvm/default-java

small_install:
	for f in *.kv *.py android.txt *.so; do \
		adb push $$f /mnt/sdcard/net.ardoe.hakan.gedtree; \
	done
log:
	adb logcat | grep -i python
apk: install
	cd $(BUILDDIR) && JAVA_HOME=$(JAVA_HOME) python2.7 build.py $(BUILDARGS) --version $(VERSION).`date +%s` debug installd


release: install release-apk
	grep -v ONLY_IN_FREE_VERSION  gedtree.py > dist/gedtree.py
	python -O -m compileall  dist
	rm dist/gedtree.py
	$(MAKE) FREE='' release-apk

release-apk:
	cd $(BUILDDIR) && JAVA_HOME=$(JAVA_HOME) python2.7 build.py $(BUILDARGS) --version $(VERSION) release installr
	jarsigner $(BUILDDIR)/bin/GedTree$(FREE)-$(VERSION)-release-unsigned.apk hakan
	/usr/local/src/android-sdk-linux/tools/zipalign -v 4 \
			$(BUILDDIR)/bin/GedTree$(FREE)-$(VERSION)-release-unsigned.apk \
			GedTree$(FREE)-$(VERSION)-release.apk
	cp GedTree$(FREE)-$(VERSION)-release.apk /tmp

install:
	-rm -r dist
	mkdir dist
	python -O -m compileall  .
	cp -r gedtree.pyo gedtree.kv main.py ansel.py \
	   button.png button_pressed.png menu-background.png \
	   simplepyged \
	   dist
	bash -c 'rm dist/simplepyged/{*.py,*.pyc}'
	cp example.ged dist/example.ged
