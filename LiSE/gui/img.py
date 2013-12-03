# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
from os import sep
from os.path import abspath

from LiSE import __path__
from LiSE.util import SaveableMetaclass


"""Saveable records about image files."""


imgrows = [
    ('default_wallpaper', ['wallpape.jpg'], 0, 0),
    ('default_spot', ['orb.png'], 0, 0),
    ('default_pawn', ['rltiles', 'hominid', 'unseen.bmp'], 1, 0),
    ('enter_shop', ['rltiles', 'enter_shop.bmp'], 1, 0),
    ('house', ['pixel-city', 'house.png'], 0, 0),
    ('tile-flat', ['pixel-city', 'tile-flat.png'], 0, 5),
    ('block', ['pixel-city', 'tile-block.png'], 0, 13),
    ('bldg-brown', ['pixel-city', 'bldg-brown.png'], 0, 8),
    ('bldg-orange', ['pixel-city', 'bldg-orange.png'], 0, 8),
    ('bldg-red', ['pixel-city', 'bldg-red.png'], 0, 8),
    ('bldg-light', ['pixel-city', 'bldg-light.png'], 0, 5),
    ('bldg-lightest', ['pixel-city', 'bldg-lightest.png'], 0, 7),
    ('bldg-ground', ['pixel-city', 'bldg-ground.png'], 0, 6),
    ('bldg-darkest', ['pixel-city', 'bldg-light.png'], 0, 7),
    ('bldg-darker', ['pixel-city', 'bldg-light.png'], 0, 8),
    ('bldg-dark', ['pixel-city', 'bldg-light.png'], 0, 6)]
"""Some special names for the default values.

These need to be inserted in Python, rather than SQL, because the
database will use absolute paths for all the image files, and SQLite
is not clever enough to translate relative paths to absolute.

"""


imgvalfmt = "('{0}', '" + abspath(__path__[-1]) + sep + "{1}', {2}, {3})"
"""A format string in which to insert values from `imgrows` to make
their relative paths absolute.

Actually this just prepends the path that the LiSE module is in to the
path given in the 1th format argument.

"""

spot_imgs = ('bldg-dark', 'bldg-darker', 'bldg-darkest',
             'bldg-light', 'bldg-lightest', 'bldg-brown',
             'bldg-orange', 'bldg-red', 'bldg-ground',
             'tile-flat', 'block', 'house')


tagrows = [(img, 'spot') for img in spot_imgs]


tagvalfmt = "('{}', '{}')"


class Img(object):
    """A class for keeping track of the various image files that go into
    the GUI.

    This class should never be instantiated, nor even subclassed. It
    exists to save and load records. If you want to display an :class:`Img`,
    use :class:`~kivy.uix.image.Image`.

    """
    __metaclass__ = SaveableMetaclass
    # I'm not sure why, but a pixel in Kivy is three in the .png
    postlude = [
        "INSERT INTO img (name, path, rltile, stacking_height) VALUES "
        + ", ".join([imgvalfmt.format(
            name,
            sep.join(
                ["gui", "assets"] + path), rltile, stackh / 3)
            for (name, path, rltile, stackh) in imgrows]),
        "INSERT INTO img_tag (img, tag) VALUES "
        + ", ".join([tagvalfmt.format(img, tag)
                     for (img, tag) in tagrows])]
    tables = [
        ("img",
         {"name": "text not null",
          "path": "text not null",
          "rltile": "boolean not null DEFAULT 0",
          "stacking_height": "float not null default 0.0"},
         ("name",),
         {},
         ["stacking_height >= 0.0"]),
        ("img_tag",
         {"img": "text not null",
          "tag": "text not null"},
         ("img", "tag"),
         {"img": ("img", "name")},
         [])]
