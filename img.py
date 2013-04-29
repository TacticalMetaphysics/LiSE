# This file is for the controllers for the things that show up on the
# screen when you play.
import pyglet
from util import SaveableMetaclass


__metaclass__ = SaveableMetaclass


class Img:
    tablenames = ["img"]
    coldecls = {"img":
                {"name": "text",
                 "path": "text",
                 "rltile": "boolean"}}
    primarykeys = {"img": ("name",)}
