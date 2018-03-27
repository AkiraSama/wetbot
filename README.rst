wetbot
======
|python badge| |d.py badge|

A discord.py_ (rewrite_) based general-use personal bot.


Installation
============
The following installation methods were tested and verified on
a Debian 10 "buster" system.


Dependencies
------------
- `Python 3.6`_
- MongoDB_


Recommended Method
------------------
This installation method requires a git client and the pipenv_
packaging tool (which ultimately requires pip_, although `pipenv's
"fancy installation method" <pipenv fancy_>`_ is also recommended).

.. code-block:: console

    $ git clone https://github.com/AkiraSama/wetbot.git
    $ cd wetbot
    $ pipenv sync
    $ pipenv run python -m wetbot --help

To update your wetbot installation after using this method, it's a
simple matter of pulling the latest source version and syncing your
pipenv dependencies inside your cloned repository.

.. code-block:: console

    $ git pull
    $ pipenv sync


Basic Method
------------
This installation method requires a git client and pip_. It is
suggested that you use a virtualenv_ to manage the versions of your
packages. Various tools exist to manage virtualenvs for you, such
as the one used in the `Recommended Method`_.

.. code-block:: console

    $ git clone https://github.com/AkiraSama/wetbot.git
    $ cd wetbot
    $ python3 -m pip install --user --upgrade -r requirements.txt
    $ python3 -m wetbot --help

To update your wetbot installation after using this method, pull
the latest version of the source and upgrade the pip packages
in ``requirements.txt`` from your cloned repository.

.. code-block:: console

    $ git pull
    $ python3 -m pip install --user --upgrade -r requirements.txt


.. Resource Hyperlinks

.. _discord.py: https://github.com/Rapptz/discord.py
.. _rewrite: https://github.com/Rapptz/discord.py/tree/rewrite/
.. _Python 3.6: https://www.python.org/downloads/release/python-364/
.. _MongoDB: https://docs.mongodb.com/manual/installation/
.. _pipenv: https://docs.pipenv.org/#install-pipenv-today
.. _pipenv fancy: https://docs.pipenv.org/install/#fancy-installation-of-pipenv
.. _pip: https://pip.pypa.io/en/stable/installing/
.. _virtualenv: https://pypi.python.org/pypi/virtualenv


.. |python badge| image:: https://img.shields.io/badge/python-3.6-blue.svg
   :target: `Python 3.6`_
.. |d.py badge| image:: https://img.shields.io/badge/discord.py-rewrite-blue.svg
   :target: rewrite_
