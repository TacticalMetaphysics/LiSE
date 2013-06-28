# This file is for the controllers for the things that show up on the
# screen when you play.
from pyglet.resource import image
from util import SaveableMetaclass, dictify_row


"""Container for images to be drawn, maybe."""


__metaclass__ = SaveableMetaclass


class Img:
    """A pretty thin wrapper around a Pyglet image.

Has savers and loaders that work with the LiSE database. The image
itself isn't saved, though. It's loaded, but saving an Img just means
saving the path.

    """
    tables = [
        ("img",
         {"name": "text not null",
          "path": "text not null",
          "rltile": "boolean not null DEFAULT 0"},
         ("name",),
         {},
         [])]

    def __init__(self, db, name, path, rltile):
        """Return an Img, and register it with the imgdict of the database
provided."""
        self.name = name
        self.path = path
        self.rltile = rltile
        self.tex = None
        db.imgdict[name] = self
        self.db = db

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.tex)

    def __getattr__(self, attrn):
        if attrn == 'width':
            return self.tex.width
        elif attrn == 'height':
            return self.tex.height
        elif attrn == 'center':
            return (self.tex.width/2, self.tex.height/2)
        elif attrn == 'texture':
            return self.tex
        else:
            raise AttributeError(
                "Img instance has no attribute {0}.".format(attrn))

    def get_tabdict(self):
        return {
            "img": {
                "name": self.name,
                "path": self.path,
                "rltile": self.rltile}}

    def unravel(self):
        """Load the underlying texture using pyglet.

Different loaders are used depending on if the image is a Windows
bitmap or a PNG. In the former case, a certain color value is made
transparent.

        """
        db = self.db
        if self.tex is None:
            if self.rltile:
                self.tex = load_rltile(db, self.name, self.path)
            else:
                self.tex = load_regular_img(db, self.name, self.path)

    def get_texture(self):
        return self.tex


def load_rltile(db, name, path):
    """Load a Windows bitmap, and replace ffGll -> 00Gll and ff. -> 00."""
    badimg = image(path)
    badimgd = badimg.get_image_data()
    bad_rgba = badimgd.get_data('RGBA', badimgd.pitch)
    good_data = bad_rgba.replace('\xffGll', '\x00Gll')
    good_data = good_data.replace('\xff.', '\x00.')
    badimgd.set_data('RGBA', badimgd.pitch, good_data)
    rtex = badimgd.get_texture()
    return rtex


def load_regular_img(db, name, path):
    """Load an ordinary PNG image."""
    tex = image(path).get_image_data().get_texture()
    return tex


read_imgs_qryfmt = (
    "SELECT {0} FROM img WHERE name IN ({1})".format(
        ", ".join(Img.colnames["img"]), "{0}"))


def read_imgs(db, names):
    """Instantiate the Img of the given names, but don't load their
textures just yet. Return a dictionary keyed by name."""
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
    """Unravel Img previously read by read_imgs, thus loading the
textures. Return a dictionary keyed by name."""
    for img in imgd.itervalues():
        img.unravel()
    return imgd


def load_imgs(db, names):
    """Load the Img by the given names. Return a dictionary keyed by name."""
    return unravel_imgs(db, read_imgs(db, names))
