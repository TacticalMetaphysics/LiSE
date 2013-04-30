# This file is for the controllers for the things that show up on the
# screen when you play.
from pyglet.resource import image
from util import SaveableMetaclass


__metaclass__ = SaveableMetaclass


class Img:
    tablenames = ["img"]
    coldecls = {"img":
                {"name": "text",
                 "path": "text",
                 "rltile": "boolean"}}
    primarykeys = {"img": ("name",)}

    def __init__(self, name, path, rltile, db=None):
        self.name = name
        self.path = path
        self.rltile = rltile
        self.tex = None
        if db is not None:
            db.imgdict[name] = self

    def unravel(self, db):
        if self.tex is None:
            if self.rltile:
                self.tex = load_rltile(db, self.name, self.path)
            else:
                self.tex = load_regular_img(db, self.name, self.path)


def load_rltile(db, name, path):
    badimg = image(path)
    badimgd = badimg.get_image_data()
    bad_rgba = badimgd.get_data('RGBA', badimgd.pitch)
    good_data = bad_rgba.replace('\xffGll', '\x00Gll')
    good_data = good_data.replace('\xff.', '\x00.')
    badimgd.set_data('RGBA', badimgd.pitch, good_data)
    rtex = badimgd.get_texture()
    return rtex


def load_regular_img(db, name, path):
    tex = image(path).get_image_data().get_texture()
    return tex
