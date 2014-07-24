=============================
web-platform-compat
=============================

.. image:: https://travis-ci.org/jwhitlock/web-platform-compat.png?branch=master
    :target: https://travis-ci.org/jwhitlock/web-platform-compat

.. image:: https://coveralls.io/repos/jwhitlock/web-platform-compat/badge.png?branch=master
    :target: https://coveralls.io/r/jwhitlock/web-platform-compat?branch=master

The Web Platform Compatibility API will support compatability data on the
`Mozilla Developer Network`_.  This currently takes the form of browser
compatability tables, such as the one on the `CSS display property`.
The API will help centralize this data, and allow it to be kept consistant
across languages and different presentations.

.. _Mozilla Developer Network: https://developer.mozilla.org

The project started in December 2013.  The goals, requirements, and current
status are documented on the MozillaWiki_.

.. _MozillaWiki: https://wiki.mozilla.org/index.php?title=MDN/Projects/Development/CompatibilityTables

This project will implement the data store and API for compatibility data
and related resources.

Status
------

We're defining the API and the split between API-side and client-side
functionality - see the `draft API docs`_.

.. _`draft API docs`: draft/intro.html

The next step is to implement some of the API with sample data,
as an aid to the discussion.


Development
-----------

:Code:           https://github.com/jwhitlock/web-platform-compat
:Issues:         https://bugzilla.mozilla.org/buglist.cgi?quicksearch=compat-data (tracking bug)

                 https://github.com/jwhitlock/web-platform-compat/issues?state=open (documentation issues)
:Dev Docs:       https://web-platform-compat.readthedocs.org
:Mailing list:   https://lists.mozilla.org/listinfo/dev-mdn
:IRC:            irc://irc.mozilla.org/mdndev

Quickstart
----------

Install web-platform-compat::

    pip install web-platform-compat

Then use it in a project::

    import web-platform-compat