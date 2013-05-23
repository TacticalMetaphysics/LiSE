# This file is for the controllers for the things that show up on the
# screen when you play.
from pyglet.resource import image
from util import SaveableMetaclass, dictify_row


__metaclass__ = SaveableMetaclass


class Img:
    tables = [
        ("img",
         {"name": "text",
          "path": "text",
          "rltile": "boolean"},
         ("name",),
         {},
         [])]

    def __init__(self, name, path, rltile, db=None):
        self.name = name
        self.path = path
        self.rltile = rltile
        self.tex = None
        if db is not None:
            db.imgdict[name] = self

    def get_tabdict(self):
        return {
            "img": {
                "name": self.name,
                "path": self.path,
                "rltile": self.rltile}}

    def unravel(self, db):
        if self.tex is None:
            if self.rltile:
                self.tex = load_rltile(db, self.name, self.path)
            else:
                self.tex = load_regular_img(db, self.name, self.path)

    def get_texture(self):
        return self.tex

    def getwidth(self):
        return self.tex.width

    def getheight(self):
        return self.tex.height


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


read_imgs_qryfmt = (
    "SELECT {0} FROM img WHERE name IN ({1})".format(
        ", ".join(Img.colnames["img"]), "{0}"))


def read_imgs(db, names):
    qryfmt = read_imgs_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, names)
    r = {}
    for row in db.c:
        rowdict = dictify_row(row, Img.colnames["img"])
        rowdict["db"] = db
        r[rowdict["name"]] = Img(**rowdict)
    return r


def unravel_imgs(db, imgd):
    for img in imgd.itervalues():
        img.unravel(db)
    return imgd


def load_imgs(db, names):
    return unravel_imgs(db, read_imgs(db, names))
