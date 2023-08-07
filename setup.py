#!/usr/bin/env python

import sys
from setuptools import setup
sys.path.insert (1, '.')
from asterisk import __version__

with open ('README.rst') as f:
    description = f.read ()

licenses = ( 'Python Software Foundation License'
           , 'GNU Library or Lesser General Public License (LGPL)'
           )
download = "http://downloads.sourceforge.net/project/pyst/pyst"

setup \
    ( name = 'pyst'
    , version = __version__
    , description = 'A Python Interface to Asterisk'
    , long_description = ''.join (description)
    , author = 'Karl Putland'
    , author_email = 'kputland@users.sourceforge.net'
    , maintainer = 'Ralf Schlatterbeck'
    , maintainer_email = 'rsc@runtux.com'
    , url = 'http://www.sourceforge.net/projects/pyst/'
    , packages = ['asterisk']
    , license = ', '.join (licenses)
    , platforms = 'Any'
    , download_url = \
        "%(download)s/%(__version__)s/pyst-%(__version__)s.tar.gz" % locals ()
    , classifiers =
        [ 'Development Status :: 5 - Production/Stable'
        , 'Environment :: Other Environment'
        , 'Intended Audience :: Developers'
        , 'Intended Audience :: Telecommunications Industry'
        , 'Operating System :: OS Independent'
        , 'Programming Language :: Python'
        , 'Programming Language :: Python :: 2.4'
        , 'Programming Language :: Python :: 2.5'
        , 'Programming Language :: Python :: 2.6'
        , 'Programming Language :: Python :: 2.7'
        , 'Topic :: Communications :: Internet Phone'
        , 'Topic :: Communications :: Telephony'
        , 'Topic :: Software Development :: Libraries :: Python Modules'
        ] + ['License :: OSI Approved :: ' + l for l in licenses]
    )
