django-easy-vue2 Easy integration Vue.js and Django.
====================================================
Version for Python 2.7 &amp; Django 1.9

|licence|

.. |licence| image:: https://img.shields.io/pypi/l/python-dateutil.svg?style=flat-square
    :target: https://pypi.org/project/python-dateutil/
    :alt: licence


The `easy-vue` library provides easy integration Vue.js and Django.
This package variant intent to support old Python 2.7 and Django 1.9 version.
If you looking suppport for latest version of Python and Django - please refer to **django-easy-vue** (https://github.com/Alex-vz/django-easy-vue).


Installation
============
`easy-vue` can be installed from PyPI using `pip` (note that the package name is
different from the importable name)::

    pip install django-easy-vue2


Download
========


Code
====
The code and issue tracker are hosted on GitHub:
https://github.com/Alex-vz/django-easy-vue2

Features
========

* supports to mode of integration: with or without of using WebPack.

* Django Template tag for include Vue.js template and form Django template similar to .vue file.

* Django Template tag for include libs with automatic switching between minimized and development version according to DEBUG state.

* View base class for easy produse REST-like views without using other REST frameworks (but is is steel possible, if you prefer).

* Some useful utilites for work with Date and DateTime, dictionaries, e.t.c.

* For use with WebPack provides template for `webpack.config.js` and some structural solutions to able develope JavaScripts inside structure of Django's applications, with ability of crossreference between different applications.

Quick example
=============

* Include libs
* Include Vue templates
* Modular biuld with WebPack

.. doctest:: readmeexample

    >>> from dateutil.relativedelta import *
    >>> from dateutil.easter import *
    >>> from dateutil.rrule import *
    >>> from dateutil.parser import *
    >>> from datetime import *
    >>> now = parse("Sat Oct 11 17:13:46 UTC 2003")
    >>> today = now.date()
    >>> year = rrule(YEARLY,dtstart=now,bymonth=8,bymonthday=13,byweekday=FR)[0].year
    >>> rdelta = relativedelta(easter(year), today)
    >>> print("Today is: %s" % today)
    Today is: 2003-10-11
    >>> print("Year with next Aug 13th on a Friday is: %s" % year)
    Year with next Aug 13th on a Friday is: 2004
    >>> print("How far is the Easter of that year: %s" % rdelta)
    How far is the Easter of that year: relativedelta(months=+6)
    >>> print("And the Easter of that year is: %s" % (today+rdelta))
    And the Easter of that year is: 2004-04-11


Contributing
============

We welcome many types of contributions - bug reports, pull requests (code, infrastructure or documentation fixes). For more information about how to contribute to the project, see the ``CONTRIBUTING.md`` file in the repository.


Author
======

The django-evasy-vue modules was written by Alex V Zobov <alex_ins@mail.ru> starts form 2018.


Contact
=======


License
=======

MIT license.


