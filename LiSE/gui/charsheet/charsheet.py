# coding: utf-8
# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
"""Widgets displaying information about "characters," which are
collections of simulated entities and facts.

"""
from calendar import (
    CalendarLayout)
from table import TableView
from LiSE.gui.kivybits import (
    SaveableWidgetMetaclass,
    ClosetButton)
from kivy.uix.image import Image as KivyImage
from kivy.uix.modalview import ModalView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.adapters.listadapter import ListAdapter, ListView
from kivy.uix.listview import ListItemButton
from kivy.properties import (
    OptionProperty,
    AliasProperty,
    ListProperty,
    ObjectProperty)
from LiSE.data import (
    THING_LOC_TAB,
    THING_STAT_TAB,
    PLACE_STAT_TAB,
    PORTAL_LOC_TAB,
    PORTAL_STAT_TAB,
    CHAR_STAT_TAB,
    THING_LOC_CAL,
    THING_STAT_CAL,
    PLACE_STAT_CAL,
    PORTAL_ORIG_CAL,
    PORTAL_DEST_CAL,
    PORTAL_STAT_CAL,
    CHAR_STAT_CAL,
    SHEET_ITEM_TYPES,
    TABLE_TYPES,
    CALENDAR_TYPES)


class CharListAdapter(ListAdapter):
    character = ObjectProperty()

    def on_character(self, *args):
        self.redata()


class NounListAdapter(CharListAdapter):
    def redata(self, observer=None, branch=None, tick=None):
        if observer is None:
            self.data = list(getattr(
                self.character, self.itern)(branch, tick))
        else:
            facade = self.character.get_facade(observer)
            self.data = list(getattr(
                facade, self.itern)(branch, tick))


class ThingListAdapter(NounListAdapter):
    itern = 'iter_things'


def args_converter(idx, noun):
    return {
        'text': unicode(noun),
        'size_hint_y': None,
        'height': 25},


class ThingListView(ListView):
    charsheet = ObjectProperty()
    selection_mode = OptionProperty(['none', 'single', 'multiple'],
                                    default='single')

    def __init__(self, **kwargs):
        kwargs['adapter'] = ThingListAdapter(
            character=kwargs['charsheet'].character,
            selection_mode=kwargs['selection_mode'],
            args_converter=args_converter,
            allow_empty_selection=False,
            cls=ListItemButton)
        super(ThingListView, self).__init__(**kwargs)


class PlaceListAdapter(NounListAdapter):
    itern = 'iter_places'


class PlaceListView(ListView):
    charsheet = ObjectProperty()
    selection_mode = OptionProperty(['none', 'single', 'multiple'],
                                    default='single')

    def __init__(self, **kwargs):
        kwargs['adapter'] = PlaceListAdapter(
            character=kwargs['charsheet'].character,
            selection_mode=kwargs['selection_mode'],
            args_converter=args_converter,
            allow_empty_selection=False,
            cls=ListItemButton)
        super(PlaceListView, self).__init__(**kwargs)


class PortalListAdapter(NounListAdapter):
    itern = 'iter_portals'


class PortalListView(ListView):
    charsheet = ObjectProperty()
    selection_mode = OptionProperty(['none', 'single', 'multiple'],
                                    default='single')

    def __init__(self, **kwargs):
        kwargs['adapter'] = PortalListAdapter(
            character=kwargs['charsheet'].character,
            selection_mode=kwargs['selection_mode'],
            args_converter=args_converter,
            allow_empty_selection=False,
            cls=ListItemButton)
        super(PortalListView, self).__init__(**kwargs)


class NounStatListAdapter(ListAdapter):
    nouns = ObjectProperty()

    def redata(self, observer=None, branch=None, tick=None):
        data2b = []
        for noun in self.nouns:
            data2b.extend(noun.iter_stat_keys(observer, branch, tick))
        self.data = data2b

    def on_nouns(self, *args):
        self.redata()


class NounStatListView(ListView):
    nouns = ListProperty([])
    selection_mode = OptionProperty(['none', 'single', 'multiple'],
                                    default='single')

    def __init__(self, **kwargs):
        adapter = NounStatListAdapter(
            selection_mode=kwargs['selection_mode'],
            args_converter=args_converter,
            allow_empty_selection=False,
            cls=ListItemButton)
        kwargs['adapter'] = adapter
        super(NounStatListView, self).__init__(**kwargs)
        self.bind(nouns=adapter.setter('nouns'))
        adapter.nouns = self.nouns


class StatListView(ListView):
    charsheet = ObjectProperty()

    def __init__(self, **kwargs):
        character = kwargs['charsheet'].character
        adapter = ListAdapter(
            data=list(character.iter_stat_keys()),
            args_converter=args_converter,
            allow_empty_selection=False,
            cls=ListItemButton)
        kwargs['adapter'] = adapter
        super(StatListView, self).__init__(**kwargs)


class EditButton(ToggleButton):
    extra_listeners = ListProperty([])

    def collide_point(self, x, y):
        return super(EditButton, self).collide_point(*self.to_local(x, y))

    def on_state(self, i, v):
        for listener in self.extra_listeners:
            listener(i, v)


class Image(KivyImage):
    character = ObjectProperty()
    keys = ListProperty()
    edbut = ObjectProperty()

    def __init__(self, **kwargs):
        super(Image, self).__init__(**kwargs)
        self.size = self.texture.size


class CharSheetAdder(ModalView):
    cancel = ObjectProperty()
    confirm = ObjectProperty()
    charsheet = ObjectProperty()
    get_text = AliasProperty(
        lambda self: self.charsheet.character.closet.get_text,
        lambda self, v: None,
        bind=('charsheet',))
    selection_map = {
        "table_thing_locations": (
            THING_LOC_TAB, ["table_thing_location_things"]),
        "table_thing_stats": (
            THING_STAT_TAB, ["table_thing_stat_things",
                             "table_thing_stat_stats"]),
        "table_place_stats": (
            PLACE_STAT_TAB, ["table_place_stat_places",
                             "table_place_stat_stats"]),
        "table_portal_locations": (
            PORTAL_LOC_TAB, ["table_portal_location_portals"]),
        "table_portal_stats": (
            PORTAL_STAT_TAB, ["table_portal_stat_portals",
                              "table_portal_stat_stats"]),
        "table_general_stats": (
            CHAR_STAT_TAB, ["table_general_stat_stats"]),
        "calendar_thing_location": (
            THING_LOC_CAL, ["calendar_thing_location_thing"]),
        "calendar_thing_stat": (
            THING_STAT_CAL, ["calendar_thing_stat_thing",
                             "calendar_thing_stat_stat"]),
        "calendar_place_stat": (
            PLACE_STAT_CAL, ["calendar_place_stat_place",
                             "calendar_place_stat_stat"]),
        "calendar_portal_origin": (
            PORTAL_ORIG_CAL, ["calendar_portal_origin_portal"]),
        "calendar_portal_destination": (
            PORTAL_DEST_CAL, ["calendar_portal_destination_portal"]),
        "calendar_portal_stat": (
            PORTAL_STAT_CAL, ["calendar_portal_stat_portal",
                              "calendar_portal_stat_stat"]),
        "calendar_general_stat": (
            CHAR_STAT_CAL, ["calendar_general_stat_stat"])}

    def iter_selection(self):
        for (k, (typ, keys)) in self.selection_map.iteritems():
            outer = getattr(self.ids, k)
            if not outer.collapse:
                kwid0 = getattr(self.ids, keys[0])
                key0s = kwid0.selection
                i = 0
                for key0 in key0s:
                    if len(keys) > 1:
                        # key2 is as yet unused
                        key1 = getattr(self.ids, keys[1]).selection[i]
                    else:
                        key1 = None
                    yield self.charsheet.bonetype(
                        character=unicode(self.charsheet.character),
                        type=typ,
                        key0=key0,
                        key1=key1)
                    i += 1
                return


class CharSheet(GridLayout):
    """A display of some or all of the information making up a Character.

A CharSheet is a layout of vertically stacked widgets that are not
usable outside of a CharSheet. Those widgets are instances or
subclasses of Table, Calendar, or Image. In developer mode, each
widget has a toggle next to it that will enable editing the data
therein. The new data will be applied at the current branch and
tick.

    """
    __metaclass__ = SaveableWidgetMetaclass
    demands = ["character"]
    tables = [
        ("charsheet_item",
         {"columns":
          {"character": "TEXT NOT NULL",
           "idx": "INTEGER NOT NULL",
           "type": "INTEGER NOT NULL",
           "key0": "TEXT",
           "key1": "TEXT",
           "key2": "TEXT"},
          "primary_key":
          ("character", "idx"),
          "foreign_keys":
          {"character": ("charsheet", "character")},
          "checks":
          ["CASE key2 WHEN NULL THEN type<>{0} END".format(
              PORTAL_LOC_TAB),
           "idx in ({})".format(", ".join(
               [str(typ) for typ in SHEET_ITEM_TYPES]))
           ]
          }
         )]
    character = ObjectProperty()

    def add_item(self, i):
        # I need the layout, proper
        layout = self.parent.parent
        layout.handle_adbut(self, i)

    def repop(self, *args):
        """Iterate over the bones under my name, and add widgets appropriate
to each of them.

Each widget gets kwargs character, item_type, and
keys. item_type is an integer, defined in SHEET_ITEM_TYPE,
representing both the widget class and the way it looks up its
data. keys identify a particular entity whose data will be displayed,
but they never include branch or tick--CharSheet will only display
things appropriate to the present, whenever that may be.

        """
        _ = self.character.closet.get_text
        self.clear_widgets()
        i = 0
        height = 0
        if unicode(self.character) not in self.character.closet.skeleton[
                u"charsheet_item"]:
            # TODO: Display just the add button, and when it's
            # pressed, get input from the user and use it to build a
            # charsheet_item bone. Then display that.
            self.add_widget(
                ClosetButton(
                    closet=self.character.closet,
                    stringname=_(u'⊕'),
                    symbolic=True,
                    on_release=lambda x: self.add_item(i)))
            return
        for bone in self.character.closet.skeleton[u"charsheet_item"][
                unicode(self.character)].iterbones():
            self.size_hint = (1, None)
            keylst = [bone.key0, bone.key1, bone.key2]
            buttons = [
                ClosetButton(
                    closet=self.character.closet,
                    stringname=_(u'⊕'),
                    symbolic=True,
                    size_hint_y=0.2,
                    on_release=lambda x: self.add_item(i)),
                EditButton(
                    text=_(u'✎'),
                    group=unicode(self.character),
                    size_hint_y=0.6),
                ClosetButton(
                    closet=self.character.closet,
                    stringname=_(u'⊕'),
                    symbolic=True,
                    size_hint_y=0.2,
                    on_release=lambda x: self.add_item(i+1))]
            button_layout = GridLayout(cols=1)
            for button in buttons:
                button_layout.add_widget(button)
            if bone.type in TABLE_TYPES:
                w = TableView(
                    character=self.character,
                    item_type=bone.type,
                    keys=keylst,
                    edbut=buttons[1])
            elif bone.type in CALENDAR_TYPES:
                w = CalendarLayout(
                    character=self.character,
                    item_type=bone.type,
                    keys=keylst,
                    edbut=buttons[1])
            self.add_widget(w)
            self.add_widget(button_layout)
            self.rows_minimum[i] = w.height
            height += w.height + self.spacing[1]
            i += 1
        self.height = height

    def on_touch_down(self, touch):
        """If one of my children catches the touch, nobody else ought to, so
return True in that case."""
        for child in self.children:
            if child.on_touch_down(touch):
                return True

    def on_touch_move(self, touch):
        """Dispatch this touch to all my children."""
        for child in self.children:
            child.on_touch_move(touch)

    def on_touch_up(self, touch):
        """Dispatch this touch to all my children."""
        for child in self.children:
            child.on_touch_up(touch)

    def push_down(self, i, n):
        """Move every item after i forward n spaces."""
        items = self.character.closet.skeleton[u"charsheet_item"][unicode(
            self.character)]
        before = list(items)[:i]
        for j in xrange(i, len(items)):
            before.append(items[j]._replace(idx=items[j].idx+n))
        self.character.closet.skeleton[u"charsheet_item"][
            unicode(self.character)] = before


class CharSheetView(ScrollView):
    def on_touch_down(self, touch):
        if self.collide_point(touch.x, touch.y):
            touch.ud["charsheet"] = self.children[0]
        return super(CharSheetView, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if "charsheet" in touch.ud:
            del touch.ud["charsheet"]
        return super(CharSheetView, self).on_touch_up(touch)
