pyst: A Python Interface to Asterisk
====================================

Pyst consists of a set of interfaces and libraries to allow programming of
Asterisk from python. The library currently supports AGI, AMI, and the parsing
of Asterisk configuration files. The library also includes debugging facilities
for AGI.

News 2020: Updated to Python3 including Py7 which includes a new 'async'
keyword that was used in the code. Note that there is a pyst2 project
also on github which is a fork from an earlier version of pyst.
Unfortunately the fork was made from the old Subversion repository and
therefore the two repos do not share a common root in git which makes it
hard to merge changes. Also I've introduced a regression test since then
which afaik is not included in pyst2. The maintainers seem to have tried
to contact me via Sourceforge but this may not have worked at the time
due to problems forwarding mails by SF. This should no longer happen as
in GIT every commit from me contains my correct email address now.

So far I've tried to be compatible with the mentioned change of the
async keyword so that the API will not diverge too much. Note that there
is one ad-hoc patch in pyst2 that breaks the old API:

Newer versions of Asterisk now send the output of AMI commands prefixed
with ``Output:``.  With my version this fits nicely into the
already-implemented ``multiheaders`` variable where Lines with a
repeated header are kept.  So all the ``Output:`` lines already were
correctly parsed and put into ``self.multiheaders ['Output']``. The only
thing I had to fix was to put all these lines into the old ``data``
variable, too. So if you were using ``data`` with old versions of
asterisk your code continues to work with pyst. Conversely pyst2 has a
patch that will return ``data`` prefixed with ``Output:`` (untested,
this is how I read the code).

When I have time I intend to graft the pyst2 repo onto my working copy
(probably using reposurgeon_) and look through the changes that are
interesting. Drop me a note if you find something in pyst2 that you
think should be in pyst.

Github repo can be cloned with::

 git clone https://github.com/schlatterbeck/pyst.git


Old News: The source code is now in a GIT repository on Sourceforge.
To check out anonymously into the local directory ``pyst``, use::

 git clone git://git.code.sf.net/p/pyst/code pyst

Update 2020: I will continue to push to the sourceforge repository, too.

Thanks to Eric S. Raymond's `reposurgeon`_, it was possible to unite the
old CVS repository, the monotone repository used until 0.2 (and a little
beyond 0.2) and the recent subversion repository into one git repository
that contains the whole history and cleans up some artefacts.

.. _reposurgeon: http://www.catb.org/esr/reposurgeon/

A note on maintenance and forks:
The current maintainer is Ralf Schlatterbeck. I've contacted maintainers
of forks to try to join forces. For any questions, please contact me via
rsc@runtux.com or my sourceforge user.

Download from `Sourceforge project page`_.

.. _`Sourceforge project page`: http://sourceforge.net/projects/pyst/

Installation is the standard python install::

 tar xvf pyst.tar.gz
 cd pyst
 python setup.py install --prefix=/usr/local

Documentation is currently only in python docstrings, you can use
pythons built-in help facility::

 import asterisk
 help (asterisk)
 import asterisk.agi
 help (asterisk.agi)
 import asterisk.manager
 help (asterisk.manager)
 import asterisk.config
 help (asterisk.config)

Some notes on platforms: We now specify "platforms = 'Any'" in
``setup.py``. This means, the manager part of the package will probably
run on any platform. The agi scripts on the other hand are called
directly on the host where Asterisk is running in which case they are
limited to the platforms asterisk is running on. Alternatively, you can
use the *fastagi* mechanism of asterisk which calls the agi scripts on a
remote host. In the latter case this host can be any platform where
python runs.

Tests
-----

The tests are standard pytest-compatible tests. Run with::

    python3 -m pytest test

Credits
-------

Thanks to Karl Putland for writing the original package.
Thanks to Matthew Nicholson for maintaining the package for some years
and for handing over maintenance when he was no longer interested.

Thanks also to the people in the sourceforge project and those who just
report bugs:
Antoine Brenner,
Max Nesterov,
Sven Uebelacker
To Matthias Urlichs for maintaining the debian package (at least for
some time).

... and to unnamed contributors to earlier releases.

Things to do for pyst
---------------------

This is the original changelog merged into the readme file. I'm not so
sure I really want to change all these things (in particular the
threaded implementation looks good to me). I will maintain a section
summarizing the changes in this README, the ChangeLog won't be
maintained any longer. Detailed changes will be available in the version
control tool.

* ChangeLog:
  The ChangeLog needs to be updated from the monotone logs.

* Documentation:
  All of pyst's inline documentation needs to be updated.

* manager.py:
  This should be converted to be single threaded.  Also there is a race
  condition when a user calls manager.logoff() followed by
  manager.close().  The close() function may still call logoff again if
  the socket thread has not yet cleared the _connected flag.

  A class should be made for each manager action rather than having a
  function in a manager class.  The manager class should be adapted to
  have a send method that know the general format of the classes.

Matthew Nicholson writes on the mailinglist (note that I'm not sure I'll do
this, I'm currently satisfied with the threaded implementation):

    For pyst 0.3 I am planning to clean up the manager.py.  There are
    several know issues with the code.  No one has actually reported these
    as problems, but I have personally had trouble with these.  Currently
    manager.py runs in several threads, the main program thread, a thread to
    read from the network, and an event distribution thread.  This causes
    problems with non thread safe code such as the MySQLdb libraries.  This
    design also causes problems when an event handler throws an exception
    that causes the event processing thread to terminate.

    The second problem is with the way actions are sent.  Each action has a
    specific function associated with it in the manager object that takes
    all possible arguments that may ever be passed to that action.  This
    makes the api somewhat rigid and the Manager object cluttered.

    To solve these problems I am basically going to copy the design of my
    Astxx manager library (written in c++) and make it more python like.
    Each action will be a different object with certain methods to handle
    various tasks, with one function in the actual Manager class to send the
    action.  This will make the Manager class much smaller and much more
    flexible.  The current code will be consolidated into a single threaded
    design with hooks to have the library process events and such.  These
    hooks will be called from the host application's main loop.


Source Code Repository Access
-----------------------------

The current versions are kept in a GIT repository on Github.
You can check out the trunk with::

 git clone https://github.com/schlatterbeck/pyst.git

I will continue to push to the Sourceforge version although Bug-Reports
etc. are easier with Github. Check out from Sourceforge with::

    git clone git://git.code.sf.net/p/pyst/code pyst

There is a monotone-after-0.2 branch which contains unreleased changes
after 0.2 which were committed to the monotone repository after the
Release of Version 0.2 (which have been merged into trunk *after*
changing how manager commands to asterisk are parsed).

Released versions are tagged, see the tags in the web-interface on
Sourceforge (or use local git commands to find out)

    https://sourceforge.net/p/pyst/code/ci/master/tree/

For versions up to 0.6 the code was kept in a Subversion repository in
Sourceforge. This has been incorporated into the current GIT repository
(after cleaning up some subversion artefacts).

For versions prior to the 0.2 release when Matthew Nicholson was
maintaining pyst, the changes were kept in a `monotone`_ repository
(monotone is a free distributed version control system). This repository
has also been incorporated into the GIT repository.

.. _`monotone`: http://monotone.ca/

prior to that the sources are in the CVS repository on sourceforge which
has also been incorporated into the GIT repository.


Changes
-------

Version 0.9: Add LICENSE, pyproject.toml, remove old test harness

- Added LICENSE, the software always was dual-licensed, no LGPL update
  clause ("2.0 or later") was specified at the time. The license should
  still be GPL/LGPL 3.0 compatible due to the dual-licensing with the
  python software foundation license.
- New section in README.rst for running the tests after removing old
  test harness
- Add patch to allow connecting using IPv6

Version 0.8: Fix README.rst

Cleanup of README before releasing 0.8 on pypi.

Version 0.7: Update tests, Compatibility

Now a test for AGI exists (in addition the the existing AMI test).
Asterisk in newer versions yields output of AMI commands prefixed with
``Output:``. This was already correctly parsed into the ``multiheaders``
variable where Lines with a repeated header are kept. For
backwards-compatibility all these lines are also put into the old
``data`` variable, too. So if you were using ``data`` with old versions
of asterisk your code continues to work with pyst.
Python 3.7 has introduced a new keyword ``async``. Unfortunately we were
using this keyword as a parameter of the AMI ``originate`` call. I've
changed this to ``run_async`` (to be compatible with pyst2, I would have
named it simpy ``asynchronous``, see the commit history).

Version 0.6: Minor feature enhancements

The asterisk management interface emulator asterisk/astemu now can be
used for unit-tests of applications using asterisk.manager. We're using
this in the regression test (see test directory). But this way it is
usable by others.

- Factor asterisk emulator from regression test into own module

Version 0.5: Small install change

Fix setup.py to include download_url. This makes it installable using
intall tools like pip.

- Add download_url to setup.py
- Fix svn url after SourceForge upgrade

Version 0.4: Minor feature enhancements

Small feature extensions to AGI and Manager modules. Add a regression
test which now covers some aspects of the manager API.

- Handle events with several fields with the same name (e.g. 'Variable'
  in the 'AgentCalled' event. Thanks to Max Nesterov for the
  suggestion, implementation differs from the suggestion in SF patch
  3290869. For a use-case see the give SF patch and the regression test
  case test_agent_event.
- Allow to use AGI module in FastAGI way via TCP connection.
  This change allows you to specify the socket streams instead
  sys.stdin/sys.stdout streams. Thanks to Max Nesterov for the patch.
  Applies SF patch 3047290.
- Add regression test framework and some test cases for manager API.
- The generated ActionID for the manager interface now includes the
  process-ID, this allows several concurrent processes using the
  manager API.

Version 0.3: Minor feature enhancements

New maintainer Ralf Schlatterbeck, this is my first release, please
report any problems via the Sourceforge Bug-Tracker or email me
directly. Thanks to Karl Putland for writing the original package.
Thanks to Matthew Nicholson for maintaining the package for some years
and for handing over maintenance when he was no longer interested.
The parsing of answers from asterisk was completely rewritten. This
should fix problems people were having with commands returning embedded
'/' or empty lines. Some new manager commands added.

- Add playdtmf manager command
- add sippeers and sipshowpeer manager commands
- rewritten manager communication
- should no longer choke on '/' in answers returned from a manager
  command (fixes SF Bug 2947866)
- should now correctly parse multi-line output with embedded empty
  lines, e.g. ``mgr.command('dialplan show')``
- Bug-fix for list manipulation in ``event_dispatch``, thanks to Jan
  Mueller, see mailinglist comment from 2008-04-18
- Merge unreleased changes from repository of Matthew Nicholson
  in particular a typo in ``agi.py`` for ``set_autohangup``, and change
  of ``get_header`` methods (see Upgrading instructions). The fixed
  ``manager.command`` support is already in (with a different
  solution). The unreleased changes are also on the 0.2 branch in the
  subversion repository in case somebody is interested.

