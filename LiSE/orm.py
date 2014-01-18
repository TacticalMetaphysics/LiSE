# coding: utf-8
# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
"""Contains ``Closet``, a caching object-relational mapper with
support for time-travelling objects; the support class ``Bone``, a
named tuple that generates SQL and can be packed into an array;
``Skeleton``, the map used by ``Closet``; and various metamagic in
support.

"""
from operator import itemgetter
from array import array
import struct
import os
from os.path import sep
from re import match
import sqlite3
from collections import (
    defaultdict,
    MutableMapping,
)
# future imports
Board = None
Spot = None
Pawn = None
CharSheet = None
CharSheetView = None
Menu = None
Img = None
GamePiece = None
Atlas = None
Logger = None
Character = None
Place = None
Portal = None
Thing = None
Timestream = None
Implicator = None
from LiSE.util import (
    NEW_THING_RE,
    NEW_PLACE_RE,
    CHARACTER_RE,
    passthru,
    ListItemIterator,
    TimestreamException,
    int2pytype,
    pytype2int)
from LiSE import __path__


class BoneMetaclass(type):
    """Metaclass for the creation of :class:`Bone` and its subclasses.

    Mostly this is a reimplementation of ``namedtuple`` from the
    ``collections`` module. However, :class:`Bone` subclasses also get
    type information for their fields. This uses the type information
    to make methods to pack and unpack the subclass in an array, as
    well as perform type checking.

    """
    tabbone = {}
    """Map the name of each bone type (incidentally, also the name of its
    table) to the bone type itself."""
    packed_str_len = 128
    """When packing a string field of a bone into an array, how long
    should the string be made? It will be padded or truncated as
    needed."""

    def __new__(metaclass, clas, parents, attrs):
        """Create a new Bone class, based on the field declarations in the
        attribute _field_decls.

        _field_decls is a list of triples. In the triples, the first
        value is the field name, the second is its type (a type
        object), and the third is the default value.

        Regardless of the type of a field, all fields may be set to
        None. This is to make Bones usable in queries, which would be
        pretty pointless if you could not leave the data unspecified.

        """
        def __new__(_cls, *args, **kwargs):
            """Create new instance of {}""".format(clas)
            if len(args) == len(_cls._fields):
                return tuple.__new__(_cls, args)
            elif len(args) > 0:
                raise ValueError("Wrong number of values")
            values = []
            for fieldn in _cls._fields:
                if fieldn in kwargs:
                    if type(kwargs[fieldn]) not in (
                            _cls._types[fieldn], type(None)):
                        kwargs[fieldn] = _cls._types[fieldn](kwargs[fieldn])
                    values.append(kwargs[fieldn])
                else:
                    values.append(_cls._defaults[fieldn])
            r = tuple.__new__(_cls, tuple(values))
            return r

        @classmethod
        def getfmt(cls):
            return cls.structtyp.format

        @classmethod
        def getbytelen(cls):
            return cls.structtyp.size

        @classmethod
        def _make(cls, iterable):
            """Make a new {} object from a sequence or iterable""".format(
                clas)
            return tuple.__new__(cls, iterable)

        @property
        def packed(self):
            """Return a string of data packed according to self.format."""
            args = []
            for datum in self:
                if isinstance(datum, unicode):
                    args.append(str(datum))
                else:
                    args.append(datum)
            return self.structtyp.pack(*args)

        def _pack_into(self, arr, i):
            """Put myself into logical position i of array arr.

            Actual position is determined by multiplying i by my
            record length.

            """
            size = self.structtyp.size
            pos = i * size
            args = [arr, pos]
            for field in self._fields:
                datum = getattr(self, field)
                if isinstance(datum, unicode):
                    args.append(str(datum))
                elif datum is None:
                    if self._defaults[field] is None:
                        if self._types[field] in (str, unicode):
                            args.append(
                                '\x00' * BoneMetaclass.packed_str_len)
                        else:
                            args.append(0)
                    else:
                        args.append(self._defaults[field])
                else:
                    args.append(datum)
            self.structtyp.pack_into(*args)

        def denull(self):
            """Return a copy of myself with the nulls stripped out of
            the strings.

            """
            denulled = {}
            for field in self._fields:
                if isinstance(getattr(self, field), str):
                    denulled[field] = unicode(
                        getattr(self, field)).strip('\x00')
                    if denulled[field] == '':
                        denulled[field] = None
            return self._replace(**denulled)

        @classmethod
        def _null(cls):
            """Return an instance of {} with all fields set to
            None.""".format(cls.__name__)
            aargh = [None] * len(cls._fields)
            return cls(*aargh)

        @classmethod
        def _unpack(cls, data):
            """Return a new instance of {} with data from
            the buffer given.""".format(cls)
            return cls(*cls.structtyp.unpack(data)).denull()

        @classmethod
        def _unpack_from(cls, i, arr):
            """Return a new instance of {} using the data at the logical
            position ``i`` in array ``arr``.

            i will be multiplied by my record length before unpacking.

            """
            bytelen = cls.structtyp.size
            pos = i * bytelen
            data = cls.structtyp.unpack_from(arr, pos)
            return cls(*data).denull()

        def __repr__(self):
            """Return a nicely formatted representation string"""
            return "{}({})".format(clas, ", ".join(
                ["{}={}".format(field, getattr(self, field))
                 for field in self._fields]))

        def _replace(self, **kwds):
            """Return a new {} object replacing specified fields with new
            values""".format(clas)
            result = self._make(map(kwds.pop, self._fields, self))
            if kwds:
                raise ValueError("Got unexpected field names: {}".format(
                    kwds.keys()))
            return result

        def _mksqlins(self):
            return "INSERT INTO {} ({}) VALUES ({});".format(
                self._name, ", ".join(f for f in self._fields if
                                      getattr(self, f) is not None),
                ", ".join("?" for f in self._fields
                          if getattr(self, f) is not None))

        def _mksqldel(self):
            if hasattr(self, 'keynames'):
                kns = self.keynames
            else:
                kns = self._fields
            return "DELETE FROM {} WHERE {};".format(
                self._name,
                " AND ".join("{}={}".format(kn, "?")
                             for kn in kns))

        def __getnewargs__(self):
            """Return self as a plain tuple. Used by copy and pickle."""
            return tuple(self)

        atts = {"__new__": __new__,
                "_make": _make,
                "__repr__": __repr__,
                "_replace": _replace,
                "__getnewargs__": __getnewargs__,
                "_fields": [],
                "_types": {},
                "_defaults": {},
                "_name": clas,
                "_null": _null,
                "getfmt": getfmt,
                "getbytelen": getbytelen,
                "packed": packed,
                "sql_ins": property(_mksqlins),
                "sql_del": property(_mksqldel),
                "_unpack": _unpack,
                "_unpack_from": _unpack_from,
                "_pack_into": _pack_into,
                "denull": denull}
        atts.update(attrs)
        if '_no_fmt' not in atts:
            fmt = bytearray('@')
            for (field_name, field_type, default) in atts["_field_decls"]:
                if field_type in (unicode, str):
                    fmt.extend('{}s'.format(BoneMetaclass.packed_str_len))
                elif field_type is int:
                    fmt.append('l')
                elif field_type is float:
                    fmt.append('d')
                elif field_type is bool:
                    fmt.append('b')
                else:
                    raise TypeError(
                        "Trying to make a format string; "
                        "don't understand the type "
                        "{}".format(field_type))
            atts["structtyp"] = struct.Struct(str(fmt))
            atts["format"] = atts["structtyp"].format
            atts["size"] = atts["structtyp"].size

        i = 0
        for (field_name, field_type, default) in atts["_field_decls"]:
            atts["_fields"].append(field_name)
            atts[field_name] = property(
                itemgetter(i),
                doc="Alias for field number {}".format(i))
            atts["_types"][field_name] = field_type
            atts["_defaults"][field_name] = default
            i += 1
        r = type.__new__(metaclass, clas, parents, atts)
        BoneMetaclass.tabbone[clas] = r
        return r


class Bone(tuple):
    """A named tuple with type information. It can generate SQL of itself
    and pack itself into an array.

    :class:`Bone` is meant to represent records in a database,
    including all the restrictions that come with the database
    schema. It is used to cache these records, speeding up access.

    Each subclass of :class:`Bone` has its own fields, each with a
    particular type. These are declared in the class attribute
    ``_field_decls``, a list of triples, each containing a field name,
    its type, and its default value.

    Instances of :class:`Bone` may be constructed with keyword
    arguments. All, some, or none of the fields may be filled this
    way; those whose names are not used as keywords will be set to
    their default value. Setting a keyword argument to ``None``,
    explicitly, will always result in ``None`` occupying that field.

    To pack a :class:`Bone` into an array, use
    :method:`_pack_into`. This calls the relevant :module:`struct`
    method, supplying a format string appropriate to the field types
    specified at class creation. Retrieve the :class:`Bone` later
    using :method:`unpack_from`.

    :class:`Bone` should not be instantiated directly. Subclass it
    instead. For convenience, the class method :method:`subclass` will
    return an appropriate subclass. :method:`structless_subclass` will
    do the same, but the subclass will not be packable into arrays.

    """
    __metaclass__ = BoneMetaclass
    _field_decls = []

    def __init__(self, *args, **kwargs):
        """Refuse to initialize :class:`Bone` directly.

        Please use the class method :method:`subclass` (or
        :method:`structless_subclass` for weird data) to make your
        own.

        """
        if self.__class__ is Bone:
            raise NotImplementedError("Bone is an abstract class.")
        super(Bone, self).__init__(*args, **kwargs)

    @classmethod
    def subclass(cls, name, decls):
        """Return a subclass of :class:`Bone` named ``name`` with field
        declarations ``decls``.

        Field declarations look like:

        ``(field_name, field_type, default)``

        field_name is a string; it will be the name of a property of the class.

        field_type is a type object. It should be one of the types
        supported by the :module:`struct` module, or you will get
        errors. You can still use ``structless_subclass`` if you need
        weird types; you just won't be able to keep your bones in
        arrays.

        ``default`` is the default value of the field, for when you
        construct a bone with keyword arguments that do not include
        this field.

        """
        d = {"_field_decls": decls}
        return type(name, (cls,), d)

    @classmethod
    def structless_subclass(cls, name, decls):
        """Return a subclass of :class:`Bone` named ``name`` with field
        declarations ``decls``. This subclass will not be packable
        into arrays.

        Field declarations look like:

        ``(field_name, field_type, default)``

        field_name is a string; it will be the name of a property of the class.

        field_type is a type object. The values of this field must
        match it, except that any field may be ``None``.

        ``default`` is the default value of the field, for when you
        construct a bone with keyword arguments that do not include
        this field.

        """
        d = {"_field_decls": decls,
             "_no_fmt": True}
        return type(name, (cls,), d)


class PlaceBone(Bone):
    _field_decls = [("host", unicode, None), ("place", unicode, None),
                    ("branch", int, 0), ("tick", int, 0)]


class Skeleton(MutableMapping):
    """A tree structure full of :class:`Bone`. Used to cache the database.

    Skeleton is used to store a cache of some or all of the LiSE
    database. It does not, itself, synchronize with the
    database--Closet and SaveableMetaclass handle that--but it
    supports union and difference operations, as though it were a
    set. This makes it easy to decide which records to save.

    Nearly everything in LiSE keeps its data in a single, enormous
    Skeleton, which itself is kept in an instance of Closet. Whenever
    you want a LiSE object, you should get it by calling some
    appropriate method in the single instance of Closet used by that
    instance of LiSE. The method will require keys for
    arguments--these are the same keys you would use to look up a
    record in one of the tables that the object refers to. The object
    you get this way will not really contain any data apart from the
    key and the Closet--whenever it needs to know something, it will
    ask Closet about it, and Closet will look up the answer in
    Skeleton, first loading it in from disc if necessary.

    Apart from simplifying the process of saving, this approach also
    makes LiSE's time travel work. The keys that identify LiSE objects
    are only partial keys--they do not specify time. Every record in
    the database and the Skeleton is also keyed by the time at which
    that record was written--not "real" time, but simulated time,
    measured in ticks that represent the smallest significant
    time-span in your simulation. They are also keyed with a branch
    number, indicating which of several alternate histories the record
    is about. When you refer to properties of a LiSE object, you get
    data from only one branch of one tick--the most recent data with
    respect to the time the simulation is at, in the branch the
    simulation is at, but ignoring any data whose tick is later than
    the tick the simulation is at. The simulation's "present" branch
    and tick are attributes of its Closet. The user may set them
    arbitrarily, and thereby travel through time.

    The "leaves" at the lowest level of a Skeleton are instances of
    some subclass of :class:`Bone`. The API for :class:`Bone` is made
    to resemble an ordinary Python object with properties full of
    data, with type checking. Treat it that way; the only caveat is
    that any :class:`Skeleton` with any type of :class:`Bone` in its
    values cannot hold any other type. This helps with data integrity,
    as the corresponding table in the database has that
    :class:`Bone`'s fields and none other. It also allows for
    optimization using :module:`array` and :module:`struct`. See the
    documentation of :class:`Bone` for details.

    Iteration over a :class:`Skeleton` is a bit unusual. The usual
    iterators over mappings are available, but they will proceed in
    ascending order of the keys if, and only if, the keys are
    integers. Otherwise they are in the same order as a
    dictionary. :class:`Skeleton` also provides the special generator
    method :method:`iterbones`, which performs a depth-first
    traversal, yielding only the :class:`Bone`s.

    Several methods are made purely for the convenience of time
    travel, particularly :method:`value_during`, which assumes that
    the keys are ticks, and returns the :class:`Bone` of the latest
    tick less than or equal to the present tick.

    There is a primitive event handling infrastructure built into
    :class:`Skeleton`. Functions in the list :attribute:`listeners`
    will be called with the :class:`Skeleton` object, the key, and the
    value of each assignment to the :class:`Skeleton`, or to any other
    :class:`Skeleton` contained by that one, however
    indirectly. Likewise with each deletion, though in that case, the
    value is not supplied. This feature exists for the convenience of
    the user interface code.

    """
    def __init__(self, content=None, name="", parent=None):
        """Technically all of the arguments are optional but you should really
        specify them whenever it's reasonably sensible to do
        so. ``content`` is a mapping to crib from, ``parent`` is who to
        propagate events to, and ``name`` is mostly for printing.

        """
        self.content = {}
        self._set_listeners = []
        self._del_listeners = []
        """Functions to call when something changes, either in my content, or
        in that of some :class:`Skeleton` I contain, however indirectly.

        """
        self.name = name
        """A string for representing myself."""
        self.parent = parent
        """Some other :class:`Skeleton` to propagate events to. Can be
        ``None``.

        """
        """My data, a :type:`dict` by default. It may become a :type:`list` or
        :type:`array` when its first key is assigned."""
        if content is not None:
            self._populate_content(content)

    def _populate_content(self, content):
        """Fill myself with content."""
        if content in (None, {}, []):
            return
        if content.__class__ in (dict, self.__class__):
            kitr = content.iteritems()
        else:
            kitr = ListItemIterator(content)
        for (k, v) in kitr:
            if hasattr(v, 'content'):
                # It's a Skeleton.
                # Add a copy of it, unless there's no data to copy,
                # in which case don't bother.
                if len(v.content) == 0:
                    self[k] = None
                else:
                    self[k] = v.copy()
                    self[k].name = k
                    self[k].parent = self
            elif v is None or issubclass(v.__class__, Bone):
                self[k] = v
            else:
                self[k] = self.__class__(
                    content=v, name=k, parent=self)

    def __contains__(self, k):
        """Check if I have the given key"""
        if isinstance(self.content, dict):
            return k in self.content
        else:
            return k in self.ikeys

    def __getitem__(self, k):
        """Get item from ``self.content``, which may be :type:`dict`,
        :type:`list`, or :type:`array`. Unpack it in the latter
        case.

        """
        if isinstance(self.content, list):
            return self.content[k]
        elif isinstance(self.content, dict):
            return self.content[k]
        else:
            # I'm full of Bones
            return self.bonetype._unpack_from(k, self.content)

    def __setitem__(self, k, v):
        """Set item in ``self.content``, which may be :type:`dict`,
        :type:`list`, or :type:`array`. Pack it in the latter case.

        """
        if len(self.content) <= 1:
            # It's permissible to assign a Bone to a Skeleton with
            # content already in, provided the Bone immediately
            # overwrites it.
            if issubclass(v.__class__, Bone):
                self.bonetype = type(v)
                """This is the subclass of :class:`Bone` that I contain.
                Once set, only this ``bonetype`` may occupy
                ``self.content``."""
            if isinstance(k, int):
                if not hasattr(self, 'ikeys'):
                    self.ikeys = []
                    """A set of indices in ``self.content`` that contain
                    legitimate data. They will be treated like keys. Other
                    indices are regarded as empty.

                    """
                if hasattr(self, 'bonetype'):
                    if len(self.content) > 0:
                        assert(len(self.content) == 1)
                        if isinstance(self.content, dict):
                            old = next(self.content.itervalues())
                        else:
                            old = self.content[0]
                        self.content = array('c')
                        if isinstance(old, self.bonetype):
                            self.content.extend('\x00' * old.size)
                            old._pack_into(self.content, 0)
                elif len(self.content) > 0:
                    assert(len(self.content) == 1)
                    if isinstance(self.content, dict):
                        assert(next(self.content.iterkeys()) == 0)
                        old = next(self.content.itervalues())
                    else:
                        old = self.content[0]
                    self.content = [old]
                else:
                    self.content = []
        if hasattr(self, 'ikeys') and v is not None:
            if len(self.ikeys) == 0:
                self.ikeys = [k]
            elif k not in self.ikeys:
                i = 0
                end = True
                for ik in self.ikeys:
                    if ik > k:
                        self.ikeys.insert(i, k)
                        end = False
                        break
                    i += 1
                if end:
                    self.ikeys.append(k)
        if hasattr(self, 'bonetype'):
            if not isinstance(v, self.bonetype):
                raise TypeError(
                    "Skeletons that contain one Bone type may "
                    "only contain that type.")
            if isinstance(self.content, array):
                # Pad self.content with nulls until it's big enough.
                diff = (k+1) * v.size - len(self.content)
                if diff > 0:
                    self.content.extend('\x00' * diff)
        elif isinstance(self.content, list):
            # Pad self.content with None until it's big enough.
            diff = k + 1 - len(self.content)
            if diff > 0:
                self.content.extend([None] * diff)
        ### actually set content to value
        ### only if i didn't have it that way though.
        if k in self and self[k] == v:
            return
        if issubclass(v.__class__, Bone):
            if isinstance(self.content, array):
                v._pack_into(self.content, k)
            else:
                self.content[k] = v
        elif isinstance(v, self.__class__):
            v.name = k
            v.parent = self
            self.content[k] = v
        else:
            self.content[k] = self.__class__(v, name=k, parent=self)
        for listener in self._set_listeners:
            listener(self.parent, self, k, v)
        if hasattr(self.parent, 'on_child_set'):
            self.parent.on_child_set(self, k, v)

    def on_child_set(self, child, k, v):
        """Call all my listeners with args (child, k, v)."""
        for listener in self._set_listeners:
            listener(self, child, k, v)
        if hasattr(self.parent, 'on_child_set'):
            self.parent.on_child_set(child, k, v)

    def register_set_listener(self, fun):
        """Register a function to be called when a value is set on this or a
        child."""
        self._set_listeners.append(fun)

    def unregister_set_listener(self, fun):
        while fun in self._set_listeners:
            self._set_listeners.remove(fun)

    def __delitem__(self, k):
        """If ``self.content`` is a :type:`dict`, delete the key in the usual
        way. Otherwise, remove the key from ``self.ikeys``."""
        v = self.content[k]
        if isinstance(self.content, dict):
            del self.content[k]
        else:
            self.ikeys.remove(k)
        for listener in self._del_listeners:
            listener(self.parent, self, k, v)
        if hasattr(self.parent, 'on_child_del'):
            self.parent.on_child_del(self, k, v)

    def on_child_del(self, child, k, v):
        """Call all my listeners with args (child, k, v)."""
        for listener in self._del_listeners:
            listener(self, child, k, v)
        if hasattr(self.parent, 'on_child_del'):
            self.parent.on_child_del(child, k, v)

    def register_del_listener(self, fun):
        """Register a function to be called when an element is deleted in this
        or a child."""
        self._del_listeners.append(fun)

    def unregister_del_listener(self, fun):
        while fun in self._del_listeners:
            self._del_listeners.remove(fun)

    def _loud_toggle(self):
        def skel_set_printer(skel, child, k, v):
            """Debugging function to print out assignments to some skeleton or
other

            """
            Logger.debug("%s: %s[%s]=%s", skel.name, child.name, k, v)

        def skel_del_printer(skel, child, k):
            """Debugging function to print out deletions from some skeleton"""
            Logger.debug("%s: del %s[%s]", skel.name, child.name, k)

        if hasattr(self, 'loud'):
            self.unregister_set_listener(skel_set_printer)
            self.unregister_del_listener(skel_del_printer)
        else:
            self.register_set_listener(skel_set_printer)
            self.register_del_listener(skel_del_printer)
            self.loud = True

    def __iter__(self):
        """Iterate over my keys--which, if ``self.content`` is not a
        :type:`dict`, should be taken from ``self.ikeys`` and sorted first."""
        if isinstance(self.content, dict):
            return iter(self.content)
        else:
            return iter(self.ikeys)

    def __len__(self):
        """Return the number of "live" data that I have. If ``self.content``
        is not a :type:`dict`, that means the number of keys that
        point to something meaningful.

        """
        if isinstance(self.content, dict):
            return len(self.content)
        else:
            return len(self.ikeys)

    def __repr__(self):
        """If ``self.content`` is an :type:`array`, unpack the lot of
        it for show. Otherwise just return ``repr(self.content)``."""
        if isinstance(self.content, array):
            return repr([bone for bone in self.itervalues()])
        return repr(self.content)

    def __iadd__(self, other):
        """Wrapper for ``self.update`` that returns ``self``."""
        self.update(other)
        return self

    def __add__(self, other):
        """Return a copy of ``self`` that's been updated with ``other``."""
        selfie = self.copy()
        selfie.update(other)
        return selfie

    def __isub__(self, other):
        """Remove everything in me and my children that is in ``other``
        or its children. Return myself."""
        for (k, v) in other.iteritems():
            if k not in self:
                continue
            elif v == self[k]:
                del self[k]
            elif isinstance(self[k], Skeleton) and isinstance(v, Skeleton):
                self[k] -= v
            # otherwise, just keep it
        return self

    def __sub__(self, other):
        """Return a copy of myself that's had anything matching anything in
        ``other`` removed."""
        selfie = self.copy()
        selfie -= other
        return selfie

    def __str__(self):
        """Return my name, stringly."""
        return str(self.name)

    def __unicode__(self):
        """Return my name, unicodely."""
        return unicode(self.name)

    def keys(self):
        """If I contain a :type:`dict`, use its keys, otherwise
        ``self.ikeys``"""
        if isinstance(self.content, dict):
            return self.content.keys()
        else:
            return self.ikeys

    def key_before(self, k):
        """Return my largest key that is smaller than ``k``."""
        if hasattr(self, 'ikeys'):
            if k in self.ikeys:
                iki = self.ikeys.index(k)
                if iki == 0:
                    return None
                else:
                    return self.ikeys[iki-1]
            else:
                return max([j for j in self.ikeys if j < k])
        return max([j for j in self.content.keys() if j < k])

    def key_or_key_before(self, k):
        """Return my highest key less than or equal to ``k``."""
        if hasattr(self, 'ikeys'):
            if k in self.ikeys:
                return k
            else:
                return self.key_before(k)
        if k in self.content:
            return k
        else:
            return self.key_before(k)

    def value_during(self, k):
        """Return my value at ``k``, or the most recent before ``k`` if I
        don't have one exactly at ``k``.

        """
        try:
            return self[self.key_or_key_before(k)]
        except ValueError:
            return None

    def key_after(self, k):
        """Return my smallest key larger than ``k``."""
        if hasattr(self, 'ikeys'):
            if k in self.ikeys:
                iki = self.ikeys.index(k)
                if iki == len(self.ikeys) - 1:
                    return None
                else:
                    return self.ikeys[iki + 1]
            else:
                return min([j for j in self.ikeys if j > k])
        return min([j for j in self.content.keys() if j > k])

    def key_or_key_after(self, k):
        """Return ``k`` if it's a key I have, or else my
        smallest key larger than ``k``."""
        if hasattr(self, 'ikeys'):
            if k in self.ikeys:
                return k
            else:
                return self.key_after(k)
        if k in self.content:
            return k
        else:
            return self.key_after(k)

    def copy(self):
        """Return a shallow copy of myself. Changes to the copy won't affect
        *me* but will affect any mutable types *inside* me."""
        if isinstance(self.content, array):
            r = self.__class__()
            r.bonetype = self.bonetype
            r.name = self.name
            r.content = self.content
            r.ikeys = list(self.ikeys)
            return r
        elif hasattr(self, 'bonetype'):
            r = {}
            if isinstance(self.content, list):
                for k in self.ikeys:
                    r[k] = self.content[k]
            else:
                for (k, v) in self.content.iteritems():
                    r[k] = v
            return self.__class__(content=r)
        elif isinstance(self.content, list):
            r = {}
            for k in self.ikeys:
                if isinstance(self.content[k], self.__class__):
                    r[k] = self.content[k].copy()
                else:
                    r[k] = self.content[k]
            return self.__class__(content=r)
        else:
            r = {}
            for (k, v) in self.content.items():
                if isinstance(v, self.__class__):
                    if len(v.content) == 0:
                        r[k] = None
                    else:
                        r[k] = v.copy()
                        r[k].parent = self
                        r[k].name = k
                elif v is None or issubclass(v.__class__, Bone):
                    r[k] = v
            return self.__class__(content=r)

    def deepcopy(self):
        """Return a new :class:`Skeleton` with all of my data in it, no matter
        how many layers I have to recurse."""
        r = {}
        for (k, v) in self.iteritems():
            if hasattr(v, 'deepcopy'):
                r[k] = v.deepcopy()
            else:
                assert(issubclass(v.__class__, Bone))
                r[k] = v
        return self.__class__(
            content=r, name=self.name, parent=self.parent)

    def update(self, skellike):
        """Make my content match that of ``skellike``, which may be a
        :class:`Skeleton` or a :type:`dict`."""
        for (k, v) in skellike.iteritems():
            if issubclass(v.__class__, Bone):
                self[k] = v
            elif isinstance(v, self.__class__):
                if k in self.content:
                    self[k].update(v)
                else:
                    self[k] = v.deepcopy()
            else:
                assert(v.__class__ in (dict, list))
                if k in self.content:
                    self[k].update(v)
                else:
                    self[k] = self.__class__(
                        content=v, name=k, parent=self)

    def itervalues(self):
        if isinstance(self.content, array):
            for i in self.ikeys:
                yield self.bonetype._unpack_from(i, self.content)
        else:
            for v in super(Skeleton, self).itervalues():
                yield v

    def iterbones(self):
        """Perform a depth-first traversal over all :class:`Bone` objects I
        contain, however indirectly.

        The traversal follows the order of integer keys,
        where they are present.

        """
        if isinstance(self.content, dict):
            for contained in self.content.itervalues():
                if issubclass(contained.__class__, Bone):
                    yield contained
                else:
                    for bone in contained.iterbones():
                        yield bone
        elif hasattr(self, 'bonetype'):
            for bone in self.itervalues():
                yield bone
        else:
            for i in self.ikeys:
                for bone in self.content[i].iterbones():
                    yield bone

    def get_timely(self, keys, branch, tick):
        ptr = self
        for key in keys:
            ptr = ptr[key]
        return ptr[branch].value_during(tick)

    def set_timely(self, keys, value, branch, tick):
        ptr = self
        for key in keys:
            ptr = ptr[key]
        if branch not in ptr:
            ptr[branch] = []
        ptr[branch][tick] = value

    def del_timely(self, keys, branch, tick):
        ptr = self
        for key in keys:
            ptr = ptr[key]
        if branch not in ptr:
            raise KeyError("Branch doesn't exist")
        if tick not in ptr[branch]:
            tick = ptr[branch].key_before(tick)
        if not isinstance(tick, int):
            raise KeyError(
                "No value in branch {} at or before tick {}".format(
                    branch, tick))
        del ptr[branch][tick]


class SaveableMetaclass(type):
    """SQL strings and methods relevant to the tables a class is about.

    Table declarations
    ==================

    Classes with this metaclass need to be declared with an attribute
    called tables. This is a sequence of tuples. Each of the tuples is
    of length 5. Each describes a table that records what's in the
    class.

    The meaning of each tuple is thus:

    ``(name, column_declarations, primary_key, foreign_keys, checks)``

    ``name`` is the name of the table as sqlite3 will use it.

    ``column_declarations`` is a dictionary. The keys are field names, aka
    column names. Each value is the type for its field, perhaps
    including a clause like DEFAULT 0.

    ``primary_key`` is an iterable over strings that are column names as
    declared in the previous argument. Together the columns so named
    form the primary key for this table.

    ``foreign_keys`` is a dictionary. Each foreign key is a key here, and
    its value is a pair. The first element of the pair is the foreign
    table that the foreign key refers to. The second element is the
    field or fields in that table that the foreign key points to.

    ``checks`` is an iterable over strings that will end up in a CHECK(...)
    clause in sqlite3.

    A class of :class:`SaveableMetaclass` can have any number of such
    table-tuples. The tables will be declared in the order they appear
    in the tables attribute.


    Dependencies and Custom SQL
    ===========================

    The LiSE database schema uses a lot of foreign keys, which only
    work if they refer to a table that exists. To make sure it does,
    the class that uses a foreign key will have the names of the
    tables it points to in a class attribute called ``demands``. The
    tables demanded are looked up in other classes' attribute called
    ``provides`` to ensure they've been taken care of. Both attributes
    are :type:`set`s.``provides`` is generated automatically, but will
    accept any additions you give it, which is occasionally necessary
    when a class deals with SQL that is not generated in the usual
    way.

    If you want to do something with SQL that
    :class:`SaveableMetaclass` does not do for you, put the SQL
    statements you want executed in :type:`list` attributes on the
    classes, called ``prelude`` and ``postlude``. All statements in
    ``prelude`` will be executed prior to declaring the first table in
    the class. All statements in ``postlude`` will be executed after
    declaring the last table in the class. In both cases, they are
    executed in the order of iteration, so use a sequence type.

    """
    clasd = {}
    saveables = []
    """Tuples of information about saveable classes. These may be used to
    apply the database schema."""
    saveable_classes = []
    """Classes that use SaveableMetaclass"""
    tabclas = {}
    """Maps the name of each table to the class it was declared in."""
    primarykeys = {}
    """Map the name of each table to the names of the fields in its
    primary key, in a tuple."""
    colnamestr = {}
    """Map the name of each table to the names of its fields, in a string."""
    colnames = {}
    """Map the name of each table to the names of its fields, in a tuple."""
    schemata = {}
    """Map the name of each table to its schema."""

    def __new__(metaclass, clas, parents, attrs):
        """Return a new class with all the accoutrements of
        :class:`SaveableMetaclass`.

        """
        if clas in SaveableMetaclass.clasd:
            return SaveableMetaclass.clasd[clas]
        tablenames = []
        "Names of tables declared in the ``tables`` attribute of ``clas``."
        foreignkeys = {}
        """Keys: table names. Values: dictionaries with keys of table names
        *linked to*, values of tuples of field names linked to."""
        coldecls = {}
        """Unprocessed column declarations, the 1th item of a tuple in a
        ``tables`` attribute."""
        checks = {}
        """For each table, a list of Boolean expressions meant for a
        CHECK(...) clause."""
        if 'tables' in attrs:
            tabdicts = attrs['tables']
        else:
            return type.__new__(metaclass, clas, parents, attrs)
        if 'prelude' in attrs:
            prelude = attrs["prelude"]
        else:
            prelude = []
        if 'postlude' in attrs:
            postlude = attrs["postlude"]
        else:
            postlude = []
        if 'provides' in attrs:
            provides = set(attrs["provides"])
        else:
            provides = set()
        if 'demands' in attrs:
            demands = set(attrs["demands"])
        else:
            demands = set()
        local_pkeys = {}
        """Primary keys per-table, for this class only"""
        for (name, tabdict) in tabdicts:
            tablenames.append(name)
            coldecls[name] = tabdict["columns"]
            local_pkeys[name] = tabdict["primary_key"]
            SaveableMetaclass.primarykeys[name] = tabdict["primary_key"]
            if "foreign_keys" in tabdict:
                foreignkeys[name] = tabdict["foreign_keys"]
            else:
                foreignkeys[name] = {}
            if "checks" in tabdict:
                checks[name] = tabdict["checks"]
            else:
                checks[name] = []
        keynames = {}
        valnames = {}
        coltypes = {}
        coldefaults = {}
        bonetypes = {}
        for item in local_pkeys.items():
            (tablename, pkey) = item
            keynames[tablename] = list(pkey)
        for item in coldecls.items():
            (tablename, coldict) = item
            coltypes[tablename] = {}
            coldefaults[tablename] = {}
            for (fieldname, decl) in coldict.iteritems():
                if fieldname == "branch":
                    foreignkeys[tablename][fieldname] = (
                        "timestream", "branch")
                    checks[tablename].append("branch>=0")
                cooked = decl.split(" ")
                typename = cooked[0]
                coltypes[tablename][fieldname] = {
                    "text": unicode,
                    "int": int,
                    "integer": int,
                    "bool": bool,
                    "boolean": bool,
                    "float": float}[typename.lower()]
                try:
                    default_str = cooked[cooked.index("default") + 1]
                    default = coltypes[tablename][fieldname](default_str)
                except ValueError:
                    default = None
                coldefaults[tablename][fieldname] = default
            valnames[tablename] = list(set(coldict.keys()) -
                                       set(keynames[tablename]))
        for tablename in coldecls.iterkeys():
            SaveableMetaclass.colnames[tablename] = (
                keynames[tablename] + valnames[tablename])
        for tablename in tablenames:
            bonetypes[tablename] = Bone.subclass(
                tablename,
                [(colname,
                  coltypes[tablename][colname],
                  coldefaults[tablename][colname])
                 for colname in SaveableMetaclass.colnames[tablename]])
            # assigning keynames here is kind of redundant (you could
            # look them up in bonetype.cls) but mildly convenient, and
            # serves to indicate that this bonetype was constructed by
            # SaveableMetaclass
            bonetypes[tablename].keynames = keynames[tablename]
            SaveableMetaclass.tabclas[tablename] = clas
            provides.add(tablename)
            pkey = SaveableMetaclass.primarykeys[tablename]
            fkeys = foreignkeys[tablename]
            cks = ["CHECK(%s)" % ck for ck in checks[tablename]]
            coldecs = [" ".join(it) for it in coldecls[tablename].iteritems()]
            coldecstr = ", ".join(coldecs)
            pkeycolstr = ", ".join(pkey)
            SaveableMetaclass.colnamestr[tablename] = (
                ", ".join(SaveableMetaclass.colnames[tablename]))
            pkeystr = "PRIMARY KEY (%s)" % (pkeycolstr,)
            fkeystrs = []
            for item in fkeys.items():
                if len(item[1]) == 2:
                    fkeystrs.append(
                        "FOREIGN KEY (%s) REFERENCES %s(%s)" %
                        (item[0], item[1][0], item[1][1]))
                elif len(item[1]) == 3:
                    fkeystrs.append(
                        "FOREIGN KEY ({0}) REFERENCES {1}({2}) {3}".format(
                            item[0], item[1][0], item[1][1], item[1][2]))
                else:
                    raise Exception("Invalid foreign key: {0}".format(item))
            fkeystr = ", ".join(fkeystrs)
            chkstr = ", ".join(cks)
            table_decl_data = [coldecstr]
            if len(pkey) > 0:
                table_decl_data.append(pkeystr)
            if len(fkeystrs) > 0:
                table_decl_data.append(fkeystr)
            if len(cks) > 0:
                table_decl_data.append(chkstr)
            table_decl = ", ".join(table_decl_data)
            SaveableMetaclass.schemata[
                tablename] = "CREATE TABLE {} ({})".format(
                tablename, table_decl)
        SaveableMetaclass.saveables.append(
            (tuple(demands),
             tuple(provides),
             tuple(prelude),
             tuple(tablenames),
             tuple(postlude)))

        atrdic = {
            'colnames': dict([
                (tabn, tuple(SaveableMetaclass.colnames[tabn]))
                for tabn in tablenames]),
            'colnamestr': dict([
                (tabn, unicode(SaveableMetaclass.colnamestr[tabn]))
                for tabn in tablenames]),
            'colnstr': SaveableMetaclass.colnamestr[tablenames[0]],
            'keynames': dict([
                (tabn, tuple(keynames[tabn])) for tabn in tablenames]),
            'valnames': dict([
                (tabn, tuple(valnames[tabn])) for tabn in tablenames]),
            'keyns': tuple(keynames[tablenames[0]]),
            'valns': tuple(valnames[tablenames[0]]),
            'colns': tuple(SaveableMetaclass.colnames[tablenames[0]]),
            'maintab': tablenames[0],
            'tablenames': tuple(tablenames),
            'bonetypes': bonetypes,
            'bonetype': bonetypes[tablenames[0]]}
        atrdic.update(attrs)

        clasn = clas
        clas = type.__new__(metaclass, clas, parents, atrdic)
        SaveableMetaclass.saveable_classes.append(clas)
        for bonetype in bonetypes.itervalues():
            bonetype.cls = clas
        SaveableMetaclass.clasd[clasn] = clas
        return clas


def iter_character_query_bones_named(name):
    yield Thing.bonetypes["thing"]._null()._replace(
        character=name)
    yield Portal.bonetypes["portal"]._null()._replace(
        character=name)
    yield Place.bonetypes["place_stat"]._null()._replace(
        character=name)
    yield Character.bonetypes["character_stat"]._null()._replace(
        character=name)
    yield Portal.bonetypes["portal_loc"]._null()._replace(
        character=name)
    yield Portal.bonetypes["portal_stat"]._null()._replace(
        character=name)
    yield Thing.bonetypes["thing_loc"]._null()._replace(
        character=name)
    yield Thing.bonetypes["thing_stat"]._null()._replace(
        character=name)


class Closet(object):
    """A caching object-relational mapper with support for time travelling
    objects.

    Time travelling objects are technically stateless, containing only
    their key in the main ``Skeleton`` in the ``Closet``. All their
    time-sensitive attributes are really ``property``s that look up
    the appropriate value in the ``Skeleton`` at the current branch
    and tick, given by the ``Closet``'s ``time`` property. For
    convenience, you can use the method ``timely_property`` to
    construct this kind of ``property``.

    ``Closet`` also functions as an event handler. Use
    ``register_time_listener`` for functions that need to be called
    whenever the sim-time changes.

    """
    __metaclass__ = SaveableMetaclass
    tables = [
        ("globals", {
            "columns": {
                "key": "text not null",
                "type": "integer not null default 3",
                "value": "text"},
            "primary_key": ("key",),
            "checks": ["type in ({})".format(", ".join([
                str(typ) for typ in int2pytype]))]
        }),
        ("strings", {
            "columns": {
                "stringname": "text not null",
                "language": "text not null default 'eng'",
                "string": "text not null"},
            "primary_key": ("stringname", "language")})]
    globs = ("branch", "tick", "observer", "observed", "host")
    """Names of global variables"""
    working_dicts = [
        "boardhand_d",
        "calendar_d",
        "cause_d",
        "color_d",
        "board_d",
        "effect_d",
        "menu_d",
        "menuitem_d",
        "style_d",
        "event_d",
        "character_d",
        "facade_d"]
    """The names of dictionaries where I keep objects after
    instantiation.

    """

    @property
    def time(self):
        return (self.branch, self.tick)

    def __setattr__(self, attrn, val):
        if attrn == "branch" and hasattr(self, 'branch'):
            self.upd_branch(val)
        elif attrn == "tick" and hasattr(self, 'tick'):
            self.upd_tick(val)
        elif attrn == "language" and hasattr(self, 'language'):
            self.upd_lang(val)
        else:
            super(Closet, self).__setattr__(attrn, val)

    def __init__(self, connector, gettext=passthru,
                 USE_KIVY=False, **kwargs):
        """Initialize a Closet for the given connector and path.

        With USE_KIVY, I will use the kivybits module to load images.

        """
        global Place
        global Portal
        global Thing
        global Character
        global Facade
        global Timestream
        import LiSE.model
        Place = LiSE.model.Place
        Portal = LiSE.model.Portal
        Thing = LiSE.model.Thing
        Character = LiSE.model.Character
        Facade = LiSE.model.Facade
        Timestream = LiSE.model.Timestream
        global Implicator
        import LiSE.model.event
        Implicator = LiSE.model.event.Implicator
        if USE_KIVY:
            global Board
            global Spot
            global Pawn
            global GamePiece
            from LiSE.gui.board import Board, Spot, Pawn, GamePiece
            global CharSheet
            global CharSheetView
            from LiSE.gui.charsheet import CharSheet, CharSheetView
            global Menu
            from LiSE.gui.menu import Menu
            global Img
            from LiSE.gui.img import Img
            global Atlas
            from kivy.atlas import Atlas
            global Logger
            from kivy.logger import Logger
            from kivy.core.image import Image
            self.img_d = {}
            self.img_tag_d = defaultdict(set)
            self.game_piece_d = defaultdict(list)

            def load_imgs(names):
                """Load ``Img`` objects into my ``img_d``.

                These contain texture data and some metadata."""
                r = {}

                def remember_img_bone(bone):
                    """Construct the Img and keep it in ``r``"""
                    r[bone.name] = Img(
                        closet=self,
                        name=bone.name,
                        texture=Image(bone.path).texture)
                self.select_and_set(
                    (Img.bonetypes["img"]._null()._replace(name=n)
                     for n in names), remember_img_bone)
                self.select_and_set(
                    Img.bonetypes["img_tag"]._null()._replace(name=n)
                    for n in names)
                self.img_d.update(r)
                return r

            def get_imgs(names):
                """Return a dict of ``Img`` by name, loading as needed."""
                r = {}

                def iter_unhad():
                    """Put the ones I have into ``r``; for each of the rest,
                    yield a ``Bone`` to match it

                    """
                    for name in names:
                        if name in self.img_d:
                            r[name] = self.img_d[name]
                        else:
                            yield Img.bonetypes["img"]._null()._replace(
                                name=name)

                def remember_img_bone(bone):
                    """Load the ``Img`` for ``bone`` and keep it in ``r``"""
                    r[bone.name] = Img(
                        closet=self,
                        name=bone.name,
                        texture=Image(bone.path).texture)

                self.select_and_set(iter_unhad(), remember_img_bone)
                self.select_and_set(
                    Img.bonetypes["img_tag"]._null()._replace(img=n)
                    for n in names if n not in self.img_tag_d)
                return r

            def load_imgs_tagged(tags):
                """Load ``Img``s tagged thus, return as from ``get_imgs``"""
                boned = set()
                self.select_and_set(
                    (Img.bonetypes["img_tag"]._null()._replace(
                        tag=tag) for tag in tags),
                    lambda bone: boned.add(bone.img))
                return get_imgs(boned)

            def get_imgs_tagged(tags):
                """Get ``Img``s tagged thus, return as from ``get_imgs``"""
                r = {}
                unhad = set()
                for tag in tags:
                    if tag in self.img_tag_d:
                        r[tag] = get_imgs(self.img_tag_d[tag])
                    else:
                        unhad.add(tag)
                r.update(load_imgs_tagged(unhad))
                return r

            def iter_graphic_keybones(names):
                """Yield the ``graphic`` and ``graphic_img`` bones
                for each name in turn."""
                for name in names:
                    yield GamePiece.bonetypes[
                        u"graphic"]._null()._replace(name=name)
                    yield GamePiece.bonetypes[
                        u"graphic_img"]._null()._replace(graphic=name)

            def load_game_pieces(names):
                """Load graphics into game pieces. Return a dictionary
                with one game piece per name."""
                self.select_keybones(iter_graphic_keybones(names))
                r = {}
                for name in names:
                    r[name] = GamePiece(closet=self, graphic_name=name)
                self.game_piece_d.update(r)
                return r

            def get_game_pieces(names):
                """Return a dictionary of one game piece per name,
                loading as needed."""
                r = {}
                unhad = set()
                for name in names:
                    if name in self.game_piece_d:
                        r[name] = self.game_piece_d[name]
                    else:
                        unhad.add(name)
                r.update(self.load_game_pieces(unhad))
                return r

            self.load_imgs = load_imgs
            self.get_imgs = get_imgs
            self.load_imgs_tagged = load_imgs_tagged
            self.get_imgs_tagged = get_imgs_tagged
            self.load_game_pieces = load_game_pieces
            self.load_game_piece = lambda name: load_game_pieces([name])[name]
            self.get_game_pieces = get_game_pieces
            self.get_game_piece = lambda name: get_game_pieces([name])[name]

            self.USE_KIVY = True

        self.connector = connector
        self.empty = Skeleton({"place": {}})
        for tab in SaveableMetaclass.tabclas.iterkeys():
            self.empty[tab] = {}
        self.skeleton = self.empty.copy()
        self.altered = self.empty.copy()
        self.deleted = self.empty.copy()

        self.c = self.connector.cursor()
        self.branch_listeners = []
        self.tick_listeners = []
        self.time_listeners = []

        for glob in self.globs:
            setattr(self, glob, self.get_global(glob))

        self.lisepath = __path__[-1]
        self.sep = os.sep
        self.entypo = self.sep.join(
            [self.lisepath, 'gui', 'assets', 'Entypo.ttf'])
        self.gettext = gettext

        for wd in self.working_dicts:
            setattr(self, wd, dict())

        self.timestream = Timestream(self)
        self.time_travel_history = []
        self.game_speed = 1
        self.updating = False

    def __del__(self):
        """Try to write changes to disk before dying.

        """
        self.c.close()
        self.connector.commit()
        self.connector.close()

    def listen_to_skeleton(self):
        """Arrange that I will remember each bone set into or deleted from the
        skeleton, so that I can SQL-ify them later on--and *not*
        SQL-ify any that were set when I *wasn't* listening.

        """
        self.skeleton.register_set_listener(self.upd_on_set)
        self.skeleton.register_del_listener(self.upd_on_del)

    def ignore_skeleton(self):
        """Stop paying attention to changes in the skeleton."""
        self.skeleton.unregister_set_listener(self.upd_on_set)
        self.skeleton.unregister_del_listener(self.upd_on_del)

    def get_bone_timely(self, keys, branch=None, tick=None):
        """Get the bone at the given keys and time"""
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        while branch > 0:
            try:
                return self.skeleton.get_timely(keys, branch, tick)
            except KeyError:
                branch = self.timestream.parent(branch)
        # may throw KeyError
        return self.skeleton.get_timely(keys, 0, tick)

    def timely_bone_getter(self, keys):
        """Return a function that gets the bone with the given keys, at the
        sim-time when it's called."""
        def r(branch=None, tick=None):
            return self.get_timely(keys, branch, tick)
        return r

    def set_bone_timely(self, keys, value, branch=None, tick=None):
        """Set the bone ``value`` into the skeleton with the given keys and
        sim-time."""
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        self.skeleton.set_timely(keys, value, branch, tick)

    def timely_bone_setter(self, keys):
        """Return a function that sets a bone into the skeleton at the present
        sim-time, with the keys supplied to ``timely_bone_setter``.

        """
        def r(value, branch=None, tick=None):
            self.set_timely(keys, value, branch, tick)
        return r

    def del_bone_timely(self, keys, branch=None, tick=None):
        """Delete the bone at the given keys and sim-time, or the previous
        bone if there's none at the precise tick given.

        """
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        self.skeleton.del_timely(keys, branch, tick)

    def timely_bone_deleter(self, keys):
        """Return a function to delete the bone at or before the current time
        with the keys supplied to ``timely_bone_deleter``.

        """
        def r(branch=None, tick=None):
            self.del_timely(keys, branch, tick)
        return r

    def timely_bone_property(self, keys):
        """Make a property for the most recent value of the bone with the given
        keys."""
        return property(
            self.timely_getter(keys),
            self.timely_setter(keys),
            self.timely_deleter(keys),
            "The value in {} at the current sim-time.".format(
                repr(keys)))

    def get_fact_timely(self, keys, boneatt, branch=None, tick=None):
        """Get a particular attribute of the bone with the given keys at the
        given time."""
        bone = self.get_bone_timely(keys, branch, tick)
        return getattr(bone, boneatt)

    def timely_fact_getter(self, keys, boneatt):
        """Return a function to get a particular attribute, of a particular
        bone, with keys supplied to ``timely_fact_getter``, at the current
        sim-time."""
        def r(branch=None, tick=None):
            return self.get_fact_timely(keys, boneatt, branch, tick)
        return r

    def set_fact_timely(self, keys, boneatt, val, branch=None, tick=None):
        """Set a particular field of a bone with given keys and sim-time."""
        former = self.get_bone_timely(keys, branch, tick)
        latter = former._replace(**{boneatt: val})
        self.set_bone_timely(keys, latter, branch, tick)

    def timely_fact_setter(self, keys, boneatt):
        """Return a function to set a predetermined attribute of the bone with
        the given keys, at the present sim-time."""
        def r(val, branch=None, tick=None):
            self.set_fact_timely(keys, boneatt, val, branch, tick)
        return r

    def timely_fact_property(self, keys, boneatt):
        """Return a ``property`` that gets and sets the attribute ``boneatt``
        of the bone with ``keys``.

        Deletion of bone attributes is not supported.

        """
        return property(
            self.timely_fact_getter(keys, boneatt),
            self.timely_fact_setter(keys, boneatt),
            doc="Change the {} attribute of the bone at {}.".format(
                boneatt, repr(keys)))

    def select_class_all(self, cls):
        """Load all the data from the database for the given class."""
        self.select_and_set(bonetype._null() for bonetype in
                            cls.bonetypes.itervalues())

    def upd_on_set(self, skel, child, k, v):
        """Supposing that the bone is equipped to write its own SQL, keep it
        in my ``altered_bones`` so as to do so later."""
        if hasattr(v, 'keynames'):
            self.set_bone(v, 'altered')

    def upd_on_del(self, skel, child, k, v):
        """Supposing that the bone is equipped to write its own SQL, keep it
        in my ``deleted_bones`` so as to do so later."""
        if hasattr(v, 'keynames'):
            self.set_bone(v, 'deleted')

    def select_keybone(self, kb):
        qrystr = "SELECT {} FROM {} WHERE {};".format(
            ", ".join(kb._fields),
            kb.__class__.__name__,
            " AND ".join("{}=?".format(field) for field in kb._fields
                         if getattr(kb, field) is not None))
        if " WHERE ;" in qrystr:
            # keybone is null
            self.c.execute(qrystr.strip(" WHERE ;"))
            for bone in self.c:
                yield type(kb)(*bone)
            return
        self.c.execute(qrystr, [field for field in kb if field])
        for bone in self.c:
            yield type(kb)(*bone)

    def select_keybones(self, kbs):
        for kb in kbs:
            for bone in self.select_keybone(kb):
                yield bone

    def delete_keybones_single_typ(self, typ, kbs):
        qrystr = "DELETE FROM {} WHERE {};".format(
            typ.__name__, " AND ".join(
                ["{}=?".format(field) for field in
                 typ._fields]))
        self.c.execute(qrystr, tuple(kbs))
        for row in self.c:
            yield typ(*row)

    def delete_keybones(self, kbs):
        clas_qd = defaultdict(set)
        for kb in kbs:
            clas_qd[type(kb)].add(kb)
        for (clas, kbset) in clas_qd.iteritems():
            self.delete_keybones_single_typ(clas, kbset)

    def select_and_set(self, kbs, also_bone=lambda b: None):
        for bone in self.select_keybones(kbs):
            self.set_bone(bone)
            also_bone(bone)

    def upd_branch(self, b):
        """Set the active branch, alerting any branch_listeners"""
        super(Closet, self).__setattr__('branch', b)
        self.upd_time(b, self.tick)
        for listener in self.branch_listeners:
            listener(b)

    def upd_tick(self, t):
        """Set the current tick, alerting any tick_listeners"""
        super(Closet, self).__setattr__('tick', t)
        self.upd_time(self.branch, t)
        for listener in self.tick_listeners:
            listener(t)

    def upd_time(self, b, t):
        """Set the current branch and tick, alerting any time_listeners"""
        for listener in self.time_listeners:
            listener(b, t)

    def get_global(self, key):
        self.c.execute("SELECT type, value FROM globals WHERE key=?;", (key,))
        (typ_i, val_s) = self.c.fetchone()
        return int2pytype[typ_i](val_s)

    def set_global(self, key, value):
        self.c.execute("DELETE FROM globals WHERE key=?;", (key,))
        self.c.execute(
            "INSERT INTO globals (key, type, value) VALUES (?, ?, ?);",
            (key, pytype2int[type(value)], unicode(value)))

    def get_text(self, strname):
        """Get the string of the given name in the language set at startup."""
        if strname is None:
            return ""
        elif strname == "@branch":
            return unicode(self.branch)
        elif strname == "@tick":
            return unicode(self.tick)
        else:
            return self.gettext(strname)

    def save_game(self):
        """Save all pending changes to disc."""
        Logger.debug("closet: beginning save_game")
        for glob in self.globs:
            self.set_global(glob, getattr(self, glob))
        for bone in self.deleted.iterbones():
            Logger.debug("deleting: {}".format(bone))
            self.c.execute(bone.sql_del, tuple(
                getattr(bone, f) for f in bone.keynames))
        for bone in self.altered.iterbones():
            Logger.debug("overwriting: {}".format(bone))
            self.c.execute(bone.sql_del, tuple(
                getattr(bone, f) for f in bone.keynames))
            self.c.execute(bone.sql_ins, tuple(
                getattr(bone, f) for f in bone._fields))
        self.connector.commit()
        Logger.debug("closet: saved game")

    def load_img_metadata(self):
        self.select_class_all(Img)

    def load_gfx_metadata(self):
        self.select_class_all(GamePiece)

    def load_strings(self):
        """Load all strings available."""
        self.select_and_set(self.bonetypes["strings"]._null())

    def make_generic_place(self, character):
        """Make a place hosted by the given character, and give it a boring
        name.

        """
        character = self.get_character(character)
        placen = "generic_place_{0}".format(len(character.graph.vs))
        return character.make_place(placen)

    def make_generic_thing(self, character, host, location,
                           branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        character = self.get_character(character)
        charn = unicode(character)
        hostn = unicode(host)
        locn = unicode(location)
        if charn not in self.skeleton[u"thing"]:
            self.skeleton[u"thing"][charn] = {}
        thingn = u"generic_thing_{}".format(
            len(self.skeleton[u"thing"][charn]))
        thing_core_bone = Thing.bonetypes["thing"](
            character=charn,
            name=thingn,
            host=hostn)
        self.set_bone(thing_core_bone)
        thing_loc_bone = Thing.bonetypes["thing_loc"](
            character=charn,
            name=thingn,
            branch=branch,
            tick=tick,
            location=locn)
        self.set_bone(thing_loc_bone)
        return character.make_thing(thingn)

    def load_charsheet(self, character):
        """Return a CharSheetView displaying the CharSheet for the character
        specified, perhaps loading it if necessary."""
        def gen_keybones():
            for bonetype in CharSheet.bonetypes.itervalues():
                yield bonetype._null()._replace(character=character)
        # if the character is not loaded yet, make it so
        character = unicode(self.get_character(character))
        self.select_and_set(gen_keybones())

    def get_charsheet(self, character):
        if character not in self.skeleton[u"character_sheet_item_type"]:
            self.load_charsheet(character)
        return CharSheetView(character=self.get_character(character))

    def load_characters(self, names):
        def iterkbs():
            for name in names:
                for bone in iter_character_query_bones_named(name):
                    yield(bone)
        self.select_and_set(iterkbs())

    def get_characters(self, names):
        r = {}

        def iter_unhad():
            for name in names:
                if name not in self.character_d:
                    for bone in iter_character_query_bones_named(name):
                        yield bone

        self.select_and_set(iter_unhad())
        for name in names:
            r[name] = Character(self, name)  # you can have a
                                             # character with no data
                                             # in it, that's fine
        self.character_d.update(r)
        return r

    def get_character(self, name):
        """Return the named character. Load it if needed.

        When supplied with a Character object, this will simply return
        it, so you may use it to *ensure* that an object is a
        Character.

        """
        if isinstance(name, Character):
            return name
        return self.get_characters([str(name)])[str(name)]

    def get_effects(self, names):
        """Return the named effects in a dict"""
        r = {}
        for name in names:
            r[name] = Implicator.make_effect(name)
        return r

    def get_effect(self, name):
        """Return the named effect in a dict"""
        return self.get_effects([name])[name]

    def get_causes(self, names):
        """Return the named causes in a dict"""
        r = {}
        for name in names:
            r[name] = Implicator.make_cause(name)
        return r

    def get_cause(self, cause):
        """Return the named cause in a dict"""
        return self.get_causes([cause])[cause]

    def load_board(self, observer, observed, host):
        """Load and return a graphical board widget displaying the contents of
        the host that are parts of the observed character, as seen by
        the observer character.

        """
        obsrvr = unicode(observer)
        obsrvd = unicode(observed)
        hst = unicode(host)
        keybones = [
            Board.bonetypes["board"]._null()._replace(
                observer=obsrvr, observed=obsrvd, host=hst),
            Spot.bonetypes["spot"]._null()._replace(
                host=hst),
            Spot.bonetypes["spot_coords"]._null()._replace(
                host=hst),
            Pawn.bonetypes["pawn"]._null()._replace(
                host=hst)]
        self.select_and_set(keybones)

    def get_board(self, observer, observed, host):
        """Return a graphical board widget displaying the contents of the host
        that are parts of the observed character, as seen by the
        observer character. Load it if needed.

        """
        observer = self.get_character(observer)
        observed = self.get_character(observed)
        host = self.get_character(host)
        facade = observed.get_facade(observer)
        return Board(facade=facade, host=host)

    def get_place(self, char, placen):
        """Get a place from a character"""
        return self.get_character(char).get_place(placen)

    def get_portal(self, char, name):
        """Get a portal from a character"""
        return self.get_character(char).get_portal(name)

    def get_thing(self, char, name):
        """Get a thing from a character"""
        return self.get_character(char).get_thing(name)

    def get_imgs(self, imgnames):
        """Return a dictionary full of images by the given names, loading
        them as needed."""
        r = {}
        unloaded = set()
        for imgn in imgnames:
            if imgn in self.img_d:
                r[imgn] = self.img_d[imgn]
            else:
                unloaded.add(imgn)
        if len(unloaded) > 0:
            r.update(self.load_imgs(unloaded))
        return r

    def get_img(self, imgn):
        return self.get_imgs([imgn])[imgn]

    def load_menus(self, names):
        """Return a dictionary full of menus by the given names, loading them
        as needed."""
        r = {}
        for name in names:
            r[name] = self.load_menu(name)
        return r

    def load_menu(self, name):
        """Load and return the named menu"""
        self.load_menu_items(name)
        return Menu(closet=self, name=name)

    def load_menu_items(self, menu):
        """Load a dictionary of menu item infos. Don't return anything."""
        self.update_keybone(Menu.bonetypes["menu_item"]._null()._replace(
            menu=menu))

    def load_timestream(self):
        """Load and return the timestream"""
        self.select_class_all(Timestream)
        self.timestream = Timestream(self)
        return self.timestream

    def time_travel_menu_item(self, mi, branch, tick):
        """Tiny wrapper for ``time_travel``"""
        return self.time_travel(branch, tick)

    def time_travel(self, branch, tick):
        """"Set the diegetic time to the given branch and tick.

        If the branch is one higher than the known highest branch,
        create it.

        """
        assert branch <= self.timestream.hi_branch + 1, (
            "Tried to travel to too high a branch")
        if branch == self.timestream.hi_branch + 1:
            self.new_branch(self.branch, branch, tick)
        # will need to take other games-stuff into account than the
        # thing_location
        if tick < 0:
            raise TimestreamException("Tick before start of time")
        # make it more general
        mintick = self.timestream.min_tick(branch, "thing_loc")
        if tick < mintick:
            raise TimestreamException("Tick before start of branch")
        if branch < 0:
            raise TimestreamException("Branch can't be less than zero")
        self.time_travel_history.append((self.branch, self.tick))
        if tick > self.timestream.hi_tick:
            self.timestream.hi_tick = tick
        self.branch = branch
        self.tick = tick

    def increment_branch(self, branches=1):
        """Go to the next higher branch. Might result in the creation of said
        branch."""
        b = self.branch + int(branches)
        mb = self.timestream.max_branch()
        if b > mb:
            # I dunno where you THOUGHT you were going
            self.new_branch(self.branch, self.branch+1, self.tick)
            return self.branch + 1
        else:
            return b

    def new_branch(self, parent, child, tick):
        """Copy records from the parent branch to the child, starting at
        tick."""
        assert(parent != child)
        new_bones = set()
        for character in self.character_d.itervalues():
            for bone in character.new_branch(parent, child, tick):
                new_bones.add(bone)
        for observer in self.board_d:
            for observed in self.board_d[observer]:
                for host in self.board_d[observer][observed]:
                    for bone in self.board_d[observer][observed][
                            host].new_branch(parent, child, tick):
                        new_bones.add(bone)
        self.skeleton["timestream"][child] = Timestream.bonetype(
            branch=child, parent=parent, tick=tick)
        self.timestream.hi_branch += 1
        assert(self.timestream.hi_branch == child)
        for bone in new_bones:
            self.set_bone(bone)

    def time_travel_inc_tick(self, ticks=1):
        """Go to the next tick on the same branch"""
        self.time_travel(self.branch, self.tick+ticks)

    def time_travel_inc_branch(self, branches=1):
        """Go to the next branch on the same tick"""
        self.increment_branch(branches)
        self.time_travel(self.branch+branches, self.tick)

    def go(self, nope=None):
        """Pass time"""
        self.updating = True

    def stop(self, nope=None):
        """Stop time"""
        self.updating = False

    def set_speed(self, newspeed):
        """Change the rate of time passage"""
        self.game_speed = newspeed

    def play_speed(self, mi, n):
        """Set the rate of time passage, and start it passing"""
        self.game_speed = int(n)
        self.updating = True

    def back_to_start(self, nope):
        """Stop time and go back to the beginning"""
        self.stop()
        self.time_travel(self.branch, 0)

    def end_game(self):
        """Save everything and close the connection"""
        self.c.close()
        self.connector.commit()
        self.connector.close()

    def checkpoint(self):
        """Store an image of the skeleton in its present state, to compare
        later"""
        self.old_skeleton = self.skeleton.deepcopy()

    def upbone(self, bone):
        """Raise the timestream's hi_branch and hi_tick if the bone has new
        values for them"""
        if (
                hasattr(bone, "branch") and
                bone.branch > self.timestream.hi_branch):
            self.timestream.hi_branch = bone.branch
        if (
                hasattr(bone, "tick") and
                bone.tick > self.timestream.hi_tick):
            self.timestream.hi_tick = bone.tick
        if (
                hasattr(bone, "tick_from") and
                bone.tick_from > self.timestream.hi_tick):
            self.timestream.hi_tick = bone.tick_from
        if (
                hasattr(bone, "tick_to") and
                bone.tick_to > self.timestream.hi_tick):
            self.timestream.hi_tick = bone.tick_to

    def mi_show_popup(self, mi, name):
        """Get the root LiSELayout to show a popup of a kind appropriate to
        the name given."""
        root = mi.get_root_window().children[0]
        new_thing_match = match(NEW_THING_RE, name)
        if new_thing_match:
            return root.show_pawn_picker(
                new_thing_match.groups()[0].split(", "))
        new_place_match = match(NEW_PLACE_RE, name)
        if new_place_match:
            return root.show_spot_picker(
                new_place_match.groups()[0].split(", "))
        character_match = match(CHARACTER_RE, name)
        if character_match:
            argstr = character_match.groups()[0]
            if len(argstr) == 0:
                return root.show_charsheet_maker()

    def mi_connect_portal(self, mi):
        """Get the root LiSELayout to make an Arrow, representing a Portal."""
        mi.get_root_window().children[0].make_arrow()

    def register_text_listener(self, stringn, listener):
        """Notify the listener when the string called ``stringn`` changes its
        content."""
        if stringn == "@branch" and listener not in self.branch_listeners:
            self.branch_listeners.append(listener)
        elif stringn == "@tick" and listener not in self.tick_listeners:
            self.tick_listeners.append(listener)

    def unregister_text_listener(self, stringn, listener):
        try:
            if stringn == "@branch":
                return self.unregister_branch_listener(listener)
            elif stringn == "@tick":
                return self.unregister_tick_listener(listener)
            else:
                self.skeleton["strings"][
                    stringn[1:]].set_listeners.remove(listener)
        except (KeyError, ValueError):
            raise ValueError("Listener isn't registered")

    def register_time_listener(self, listener):
        """Listener will be called when ``branch`` or ``tick`` changes"""
        if listener not in self.time_listeners:
            self.time_listeners.append(listener)

    def unregister_time_listener(self, listener):
        try:
            self.time_listeners.remove(listener)
        except ValueError:
            raise ValueError("Listener isn't registered")

    def register_branch_listener(self, listener):
        """Listener will be called when ``branch`` changes"""
        if listener not in self.branch_listeners:
            self.branch_listeners.append(listener)

    def unregister_branch_listener(self, listener):
        try:
            self.branch_listeners.remove(listener)
        except ValueError:
            raise ValueError("Listener isn't registered")

    def register_tick_listener(self, listener):
        """Listener will be called when ``tick`` changes"""
        if listener not in self.tick_listeners:
            self.tick_listeners.append(listener)

    def unregister_tick_listener(self, listener):
        try:
            self.tick_listeners.remove(listener)
        except ValueError:
            raise ValueError("Listener isn't registered")

    def register_img_listener(self, imgn, listener):
        try:
            skel = self.skeleton[u"img"][imgn]
        except KeyError:
            raise KeyError("Image unknown: {}".format(imgn))
        if listener not in skel.set_listeners:
            skel.set_listeners.append(listener)

    def unregister_img_listener(self, imgn, listener):
        try:
            skel = self.skeleton[u"img"][imgn]
        except KeyError:
            raise KeyError("Image unknown: {}".format(imgn))
        try:
            skel.set_listeners.remove(listener)
        except ValueError:
            raise ValueError("Listener isn't registered")

    def register_hi_branch_listener(self, listener):
        self.timeline.hi_branch_listeners.append(listener)

    def register_hi_tick_listener(self, listener):
        self.timeline.hi_tick_listeners.append(listener)

    def query_place(self, update=True):
        """Query the 'place' view, resulting in an up-to-date record of what
        places exist in the gameworld as it exists in the
        database.

        """
        self.c.execute("SELECT host, place, branch, tick FROM place;")
        if not update or u"place" not in self.skeleton:
            # empty it out if it exists, create it if it doesn't
            self.skeleton[u"place"] = {}
        for (host, place, branch, tick) in self.c:
            self.set_bone(PlaceBone(
                host=host,
                place=place,
                branch=branch,
                tick=tick))

    def have_place_bone(self, host, place, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        try:
            return self.skeleton[u"place"][host][place][
                branch].value_during(tick) is not None
        except (KeyError, IndexError):
            return False

    def iter_graphic_imgs(self, graphicn):
        if graphicn not in self.skeleton[u"graphic_img"]:
            return
        for bone in self.skeleton[u"graphic_img"][graphicn].iterbones():
            yield self.get_img(bone.img)

    def set_bone(self, bone, skel='main'):
        """Take a bone of arbitrary type and put it in the right place in the
        skeleton.

        Additionally, if the bone is of a kind that may implicitly
        define a place, see if the place is a new one. If so, insert a
        PlaceBone to describe it.

        """
        if skel == 'main':
            skeleton = self.skeleton
        elif skel == 'altered':
            skeleton = self.altered
        elif skel == 'deleted':
            skeleton = self.deleted
        else:
            raise ValueError("I have no skeleton named {}".format(skel))

        def init_keys(skeleton, keylst):
            for key in keylst:
                if key not in skeleton:
                    skeleton[key] = {}
                skeleton = skeleton[key]
            return skeleton

        def set_place_maybe(host, place, branch, tick):
            if not self.have_place_bone(host, place, branch, tick):
                self.set_bone(bone=PlaceBone(
                    host=host, place=place, branch=branch, tick=tick),
                    skel=skel)

        def upd_time(branch, tick):
            self.timestream.upbranch(branch)
            self.timestream.uptick(tick)

        if isinstance(bone, PlaceBone):
            init_keys(
                skeleton,
                [u"place", bone.host, bone.place, bone.branch])
            skeleton[u"place"][bone.host][bone.place][
                bone.branch][bone.tick] = bone
            return

        # Some bones implicitly declare a new place
        if Thing and isinstance(bone, Thing.bonetypes[u"thing_loc"]):
            core = skeleton[u"thing"][bone.character][bone.name]
            set_place_maybe(core.host, bone.location, bone.branch, bone.tick)
            upd_time(bone.branch, bone.tick)
        elif Thing and isinstance(bone, Thing.bonetypes[u"thing_loc_facade"]):
            core = skeleton[u"thing"][bone.observed][bone.name]
            set_place_maybe(core.host, bone.location, bone.branch, bone.tick)
            upd_time(bone.branch, bone.tick)
        elif Portal and isinstance(bone, Portal.bonetypes[u"portal_loc"]):
            core = skeleton[u"portal"][bone.character][bone.name]
            upd_time(bone.branch, bone.tick)
            for loc in (bone.origin, bone.destination):
                set_place_maybe(core.host, loc, bone.branch, bone.tick)
        elif Portal and isinstance(
                bone, Portal.bonetypes[u"portal_stat_facade"]):
            core = skeleton[u"portal"][bone.observed][bone.name]
            upd_time(bone.branch, bone.tick)
            for loc in (bone.origin, bone.destination):
                set_place_maybe(core.host, loc, bone.branch, bone.tick)
        elif Place and isinstance(bone, Place.bonetypes[u"place_stat"]):
            set_place_maybe(bone.host, bone.name, bone.branch, bone.tick)
            upd_time(bone.branch, bone.tick)
        elif Spot and isinstance(bone, Spot.bonetypes[u"spot"]):
            set_place_maybe(bone.host, bone.place, bone.branch, bone.tick)
            upd_time(bone.branch, bone.tick)
        elif Spot and isinstance(bone, Spot.bonetypes[u"spot_coords"]):
            set_place_maybe(bone.host, bone.place, bone.branch, bone.tick)
            upd_time(bone.branch, bone.tick)
        elif Img and isinstance(bone, Img.bonetypes["img_tag"]):
            if bone.tag not in self.img_tag_d:
                self.img_tag_d[bone.tag] = set()
            self.img_tag_d[bone.tag].add(bone.img)

        keynames = bone.keynames
        keys = [bone._name] + [getattr(bone, keyn) for keyn in keynames[:-1]]
        skelly = init_keys(skeleton, keys)
        final_key = getattr(bone, keynames[-1])
        skelly[final_key] = bone


def defaults(c, kivy=False):
    if kivy:
        from LiSE.data import whole_imgrows
        c.executemany(
            "INSERT INTO img (name, path, stacking_height) "
            "VALUES (?, ?, ?);",
            whole_imgrows)
        from LiSE.data import graphics
        for (name, d) in graphics.iteritems():
            c.execute(
                "INSERT INTO graphic (name, offset_x, offset_y) "
                "VALUES (?, ?, ?);",
                (name, d.get('offset_x', 0), d.get('offset_y', 0)))
            for i in xrange(0, len(d['imgs'])):
                c.execute(
                    "INSERT INTO graphic_img (graphic, layer, img) "
                    "VALUES (?, ?, ?);",
                    (name, i, d['imgs'][i]))
        from LiSE.data import stackhs
        for (height, names) in stackhs:
            qrystr = (
                "UPDATE img SET stacking_height=? WHERE name IN ({});".format(
                    ", ".join(["?"] * len(names))))
            qrytup = (height,) + names
            c.execute(qrystr, qrytup)
        from LiSE.data import boards
        for (obsrvr, obsrvd, hst) in boards:
            c.execute(
                "INSERT INTO board (observer, observed, host) "
                "VALUES (?, ?, ?);",
                (obsrvr, obsrvd, hst))
        from LiSE.data import spot_coords
        for (place, x, y) in spot_coords:
            c.execute(
                "INSERT INTO spot (place) VALUES (?);",
                (place,))
        c.executemany(
            "INSERT INTO spot_coords (place, x, y) VALUES (?, ?, ?);",
            spot_coords)
        from LiSE.data import pawns
        for observed in pawns:
            for (thing, layers) in pawns[observed].iteritems():
                i = 0
                for layer in layers:
                    c.execute(
                        "INSERT INTO pawn (observed, thing, layer, img) "
                        "VALUES (?, ?, ?, ?);",
                        (observed, thing, i, layer))
                    i += 1
    from LiSE.data import globs
    c.executemany(
        "INSERT INTO globals (key, type, value) VALUES (?, ?, ?);",
        globs)
    c.execute(
        "INSERT INTO timestream (branch, parent) VALUES (?, ?);",
        (0, 0))
    from LiSE.data import things
    for character in things:
        for thing in things[character]:
            c.execute(
                "INSERT INTO thing (character, name, host) VALUES (?, ?, ?);",
                (character, thing, things[character][thing]["host"]))
            c.execute(
                "INSERT INTO thing_loc (character, name, location) "
                "VALUES (?, ?, ?);",
                (character, thing, things[character][thing]["location"]))
    from LiSE.data import reciprocal_portals
    for (orig, dest) in reciprocal_portals:
        name1 = "{}->{}".format(orig, dest)
        name2 = "{}->{}".format(dest, orig)
        c.executemany(
            "INSERT INTO portal (name) VALUES (?);",
            [(name1,), (name2,)])
        c.executemany(
            "INSERT INTO portal_loc (name, origin, destination) VALUES "
            "(?, ?, ?);", [(name1, orig, dest), (name2, dest, orig)])
    from LiSE.data import one_way_portals
    for (orig, dest) in one_way_portals:
        name = "{}->{}".format(orig, dest)
        c.execute(
            "INSERT INTO portal (name) VALUES (?);",
            (name,))
        c.execute(
            "INSERT INTO portal_loc (name, origin, destination) "
            "VALUES (?, ?, ?);", (name, orig, dest))
    from LiSE.data import charsheet_items
    for character in charsheet_items:
        i = 0
        for (typ, key0) in charsheet_items[character]:
            c.execute(
                "INSERT INTO charsheet_item (character, type, idx, key0) "
                "VALUES (?, ?, ?, ?);", (character, typ, i, key0))
            i += 1


def mkdb(DB_NAME, lisepath, kivy=False):
    global Logger
    img_qrystr = (
        "INSERT INTO img (name, path) "
        "VALUES (?, ?);")
    tag_qrystr = (
        "INSERT INTO img_tag (img, tag) VALUES (?, ?);")

    def ins_atlas(curs, path, qualify=False, tags=[]):
        global Atlas
        if Atlas is None:
            import kivy.atlas
            Atlas = kivy.atlas.Atlas
        lass = Atlas(path)
        atlaspath = "atlas://{}".format(path[:-6])
        atlasn = path.split(sep)[-1][:-6]
        for tilen in lass.textures.iterkeys():
            imgn = atlasn + '.' + tilen if qualify else tilen
            curs.execute(img_qrystr, (
                imgn, "{}/{}".format(atlaspath, tilen)))
            for tag in tags:
                curs.execute(tag_qrystr, (imgn, tag))

    def ins_atlas_dir(curs, dirname, qualify=False, tags=[]):
        for fn in os.listdir(dirname):
            if fn[-5:] == 'atlas':
                path = dirname + sep + fn
                ins_atlas(curs, path, qualify, [fn[:-6]] + tags)

    if Logger is None:
        if kivy:
            import kivy.logger
            Logger = kivy.logger.Logger
        else:
            import logging
            Logger = logging.getLogger()
    if kivy:
        # I just need them to fill in the relevant bits of
        # SaveableMetaclass. They don't have to do anything.
        import LiSE.gui.img
        del LiSE.gui.img
        import LiSE.gui.board
        del LiSE.gui.board

    try:
        os.remove(DB_NAME)
    except OSError:
        pass
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    done = set()
    saveables = list(SaveableMetaclass.saveables)
    while saveables != []:
        (demands, provides, prelude,
         tablenames, postlude) = saveables.pop(0)
        breakout = False
        for demand in iter(demands):
            if demand not in done:
                saveables.append(
                    (demands, provides, prelude,
                     tablenames, postlude))
                breakout = True
                break
        if breakout:
            continue
        prelude_todo = list(prelude)
        while prelude_todo != []:
            pre = prelude_todo.pop()
            if isinstance(pre, tuple):
                c.execute(*pre)
            else:
                c.execute(pre)
        if len(tablenames) == 0:
            for post in postlude:
                if isinstance(post, tuple):
                    c.execute(*post)
                else:
                    c.execute(post)
            continue
        prelude_todo = list(prelude)
        try:
            while prelude_todo != []:
                pre = prelude_todo.pop()
                if isinstance(pre, tuple):
                    c.execute(*pre)
                else:
                    c.execute(pre)
        except sqlite3.OperationalError as e:
            saveables.append(
                (demands, provides, prelude_todo, tablenames, postlude))
            continue
        breakout = False
        tables_todo = list(tablenames)
        while tables_todo != []:
            tn = tables_todo.pop(0)
            Logger.debug("Building table: {}".format(tn))
            c.execute(SaveableMetaclass.schemata[tn])
            done.add(tn)
        if breakout:
            saveables.append(
                (demands, provides, prelude_todo, tables_todo, postlude))
            continue
        postlude_todo = list(postlude)
        try:
            while postlude_todo != []:
                post = postlude_todo.pop()
                if isinstance(post, tuple):
                    c.execute(*post)
                else:
                    c.execute(post)
        except sqlite3.OperationalError as e:
            Logger.warning(
                "Building {}: OperationalError during postlude: {}".format(
                    tn, e))
            saveables.append(
                (demands, provides, prelude_todo, tables_todo, postlude_todo))
            continue
        done.update(provides)

    Logger.debug("inserting default values")
    defaults(c, kivy)

    if kivy:
        Logger.debug("indexing the RLTiles")
        ins_atlas_dir(
            c, "LiSE/gui/assets/rltiles/hominid", True,
            ['hominid', 'rltile', 'pawn'])

        Logger.debug("indexing Pixel City")
        ins_atlas(c, "LiSE/gui/assets/pixel_city.atlas", False,
                  ['spot', 'pixel_city'])

    conn.commit()
    return conn


def load_closet(dbfn, gettext=None, load_img=False, load_img_tags=[],
                load_gfx=False, load_characters=[], load_charsheet=None,
                load_board=[]):
    r = Closet(connector=sqlite3.connect(dbfn), gettext=gettext,
               USE_KIVY=(load_img or load_img_tags or load_gfx or
                         load_charsheet or load_board))
    r.load_timestream()
    if load_img:
        r.load_img_metadata()
    if load_img_tags:
        r.load_imgs_tagged(load_img_tags)
    if load_gfx:
        r.load_gfx_metadata()
    if load_characters:
        r.load_characters(load_characters)
    if load_charsheet:
        r.load_charsheet(load_charsheet)
    if load_board:
        r.load_board(*load_board)
    r.listen_to_skeleton()
    return r
