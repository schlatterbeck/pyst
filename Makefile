# To use this Makefile, get a copy of my SF Release Tools
# git clone git://git.code.sf.net/p/sfreleasetools/code sfreleasetools
# And point the environment variable RELEASETOOLS to the checkout

README=README.rst
ifeq (,${RELEASETOOLS})
    RELEASETOOLS=../releasetools
endif
PKG=asterisk
PY=agi.py agitb.py astemu.py compat.py config.py __init__.py manager.py
SRC=Makefile MANIFEST.in setup.py $(README) README.html \
    $(PY:%.py=$(PKG)/%.py)

VERSIONPY=asterisk/Version.py
VERSION=$(VERSIONPY)
LASTRELEASE:=$(shell $(RELEASETOOLS)/lastrelease -n)

USERNAME=schlatterbeck
PROJECT=pyst
PACKAGE=${PROJECT}
CHANGES=changes
NOTES=notes

all: $(VERSION)

$(VERSION): $(SRC)

dist: all
	python setup.py sdist --formats=gztar,zip

clean:
	rm -f MANIFEST README.html default.css \
	    $(PKG)/Version.py $(PKG)/Version.pyc ${CHANGES} ${NOTES} \
	    upload ReleaseNotes.txt announce_pypi upload_homepage
	rm -rf dist build


release: upload upload_homepage announce_pypi announce

include $(RELEASETOOLS)/Makefile-sf
