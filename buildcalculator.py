from collections import Counter, defaultdict
from tabulate import tabulate
import json
import os

from cassiopeia import riotapi
import cassiopeia.type.core.common

buildcalculator_director = os.path.dirname(os.path.realpath(__file__))

patch = '6.3'

_fields = json.load(open(os.path.join(buildcalculator_director, 'fields.json')))
_basic_fields = json.load(open(os.path.join(buildcalculator_director, 'basic_fields.json')))


class DefaultCounter(defaultdict, Counter):
    pass


class BuildError(Exception):
    pass


class _BuildObject(object):
    def __init__(self, riot_obj, dictionary=None, default=0.0):
        self.id = riot_obj.id
        self.name = riot_obj.name

        if hasattr(riot_obj, 'stats'):  # For masteries, which don't have stats from Riot
            for attr in _fields:
                setattr(self, attr, getattr(riot_obj.stats, attr, default))
        else:
            for attr in _fields:
                setattr(self, attr, default)

        if dictionary is not None:
            dictionary = {key: DefaultCounter(float, d) for key, d in dictionary.items()}
            for attr, val in dictionary.items():
                setattr(self, attr, val)

        # 'percent_attack_speed' just doesn't exist as a stat in League of Legends. It's correct name is 'percent_base_attack_speed'
        self.percent_base_attack_speed = self.percent_attack_speed + self.percent_base_attack_speed
        self.percent_attack_speed = default

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(id(self))

    def __str__(self):
        return self.name


class Champion(_BuildObject):
    pass


class _Mastery(_BuildObject):
    # Masteries are a bit strange because their values are dictionaries.
    # Every item, rune, and champion is identical for all builds, but
    # masteries change based on the mastery page because multiple builds
    # can have different number of mastery points. Therefore we need
    # this special object to hold the dictionaries, while a 'Mastery'
    # with the correct values for all the attributes will be returned to
    # the user, based on the number of points they put in that mastery.
    def __init__(self, riot_mastery, data):
        super().__init__(riot_mastery, dictionary=data, default=DefaultCounter(float))


class Mastery(_Mastery):
    def __init__(self, mastery, points):
        self.id = mastery.id
        self.name = mastery.name
        self.points = points
        for attr in _fields:
            setattr(self, attr, getattr(mastery, attr)[points])


class Rune(_BuildObject):
    pass


class Item(_BuildObject):
    pass


class MasteryPage(object):
    _masteries = None
    _masteries_by_name = None


    def __init__(self, masteries=None, all_masteries=None):
        """@param masteries:  A dictionary of of (mastery_id, num_points) pairs. Defaults to an empty dictionary."""

        if not MasteryPage._masteries:
            MasteryPage._init_masteries(all_masteries)

        # self._selected contains the number of points given to the mastery by the user
        self._selected = defaultdict(int)
        self.update(masteries or {})
        self.list  # initializes self._iterable


    def _init_masteries(all_masteries):
        if not all_masteries:
            riotapi_masteries = {mastery.id: mastery for mastery in riotapi.get_masteries()}

            all_masteries = json.load(open(os.path.join(buildcalculator_director, 'masteries.json'.format(patch=patch))))
            all_masteries = {int(id_): data for id_, data in all_masteries.items()}
            for id_, m in all_masteries.items():
                for key, values in m.items():
                    if key != 'tree' and key != 'name':
                        m[key] = {int(i): data for i, data in values.items()}

        MasteryPage._masteries = {id_: _Mastery(riotapi_masteries[id_], data) for id_, data in all_masteries.items()}
        MasteryPage._masteries_by_name = {mastery.name: mastery for _, mastery in MasteryPage._masteries.items()}


    def update(self, masteries):
        """@param masteries:  A dictionary of (mastery_id, num_points) or (mastery_name, num_points) pairs. Previous results are not overwritten."""

        if not (isinstance(masteries, dict) or isinstance(masteries, MasteryPage)):
            raise BuildError("'masteries' must be a dictionary or a MasteryPage")

        for m, p in masteries.items():
            if isinstance(m, str):
                m = MasteryPage._masteries_by_name[m]
            elif isinstance(m, int):
                m = MasteryPage._masteries[m]
            self._selected[m] = p

        self._refresh_data = True


    @property
    def list(self):
        """Returns a list of the selected masteries (with duplicates when multiple points have been put into a mastery)
        parsed so that mastery.stats contains the correct stats value based on how many points the user put in that mastery.
        """

        if self._refresh_data:
            self._iterable = [Mastery(m, p) for m, p in self._selected.items()]
            self._refresh_data = False

        return self._iterable


    @property
    def dictionary(self):
        return {m: p for m, p in self._selected.items()}


    def __len__(self):
        return len(self._iterable)


    def __getitem(self, key):
        return self._iterable[key]


    def __iter__(self):
        return iter(self._iterable)



class RunePage(object):
    _runes = None
    _runes_by_name = None


    def __init__(self, runes=None, all_runes=None):
        """@param runes:  A dictionary of of (rune_id, point) or (rune_name, point) key/value pairs. Defaults to an empty dictionary."""

        if not RunePage._runes:
            RunePage._init_runes(all_runes)

        self._selected = defaultdict(int)
        self.update(runes or {})
        self.list  # initialize self._iterable


    def _init_runes(all_runes=None):
        if not all_runes:
            all_runes = {rune.id: rune for rune in riotapi.get_runes()}
            RunePage._runes = {id_: Rune(data) for id_, data in all_runes.items()}

        RunePage._runes_by_name = {rune.name: rune for _, rune in RunePage._runes.items()}


    def update(self, runes):
        """@param runes:  A dictionary of (rune_id, point) or (rune_name, point) pairs."""

        if not (isinstance(runes, dict) or isinstance(runes, RunePage)):
            raise BuildError("'runes' must be a dictionary or a RunePage")

        for r, p in runes.items():
            if isinstance(r, str):
                r = RunePage._runes_by_name[r]
            elif isinstance(r, int):
                r = RunePage._runes[r]
            self._selected[r] = p

        self._refresh_data = True


    @property
    def list(self):
        """Returns a list of the selected runes. Duplicates are included as additional items."""

        if self._refresh_data:
            self._iterable = [r for r, p in self._selected.items() for i in range(p)]
            self._refresh_data = False

        return self._iterable

    @property
    def dictionary(self):
        """Returns a dictionary of the selected runes."""
        return {r: p for r, p in self._selected.items()}


    def __len__(self):
        return len(self._iterable)


    def __getitem(self, key):
        return self._iterable[key]


    def __iter__(self):
        return iter(self._iterable)



class ItemSet(object):
    _items = None
    _items_by_name = None


    def __init__(self, items=None, all_items=None):
        """@param items:  A list of item IDs or item names. Defaults to an empty dictionary."""

        if not ItemSet._items:
            ItemSet._init_items(all_items)

        self._selected = [None for i in range(6)]
        self._enchantments = []
        self.set(items or [])


    def _init_items(all_items=None):
        if not all_items:
            all_items = riotapi.get_items()
            ItemSet._items = {item.id: Item(item) for item in all_items if item.maps[cassiopeia.type.core.common.Map.summoners_rift]}

        ItemSet._items_by_name = {item.name: item for _, item in ItemSet._items.items()}


    def _parse_name(self, name):
        if ' - ' in name:
            name, enchantment = name.split(' - ')
            self.enchant('Enchantment: {0}'.format(enchantment))
        return name


    def set(self, items):
        """@param items:  A list of item IDs or item names. Defaults to an empty dictionary. Any previous data is overwritten."""

        if not (isinstance(items, list) or isinstance(items, ItemSet)):
            raise BuildError("'items' must be a list or an ItemSet")

        self._enchantments = []
        for i, item in enumerate(items):
            if isinstance(item, str):
                item = self._items_by_name[self._parse_name(item)]
            elif isinstance(i, int):
                item = self._items[item]
            self._selected[i] = item


    def enchant(self, enchantment):
        """@param enchantment:  An enchantment to add to the itemset."""

        if isinstance(enchantment, str):
            enchantment = self._items_by_name[self._parse_name(enchantment)]
        elif isinstance(enchantment, int):
            enchantment = self._items[enchantment]
        self._enchantments.append(enchantment)


    @property
    def enchantments(self):
        return self._enchantments


    @property
    def list(self):
        """Returns a list of the items."""
        return [item for item in self._selected if item is not None] + self.enchantments


    def __len__(self):
        return len(self.list)


    def __getitem__(self, key):
        return self.list[key]


    def __iter__(self):
        return iter(self.list)



class Build(object):
    _champions = None
    _champions_by_name = None


    def __init__(self, champion=None, level=1, item_set=None, rune_page=None, mastery_page=None):
        """@param champion:     A champion ID or name.
        @param level:        The champion's level.
        @param item_set:     A list of item IDs or item names. Defaults to an empty dictionary.
        @param rune_page:    The rune page or a dictionary of (rune_id/rune_name, num_runes) pairs.
        @param mastery_page: The rune page or a dictionary of (mastery_id/mastery_name, num_points) pairs.
        """

        if not Build._champions:
            Build._init_champions()

        if champion is None:
            raise TypeError("Build.__init__() missing 1 required positional argument: 'champion'")
        self.set_champion(champion)
        self.set_level(level)
        self.set_items(item_set or [])
        self.set_runes(rune_page or {})
        self.set_masteries(mastery_page or {})


    def __getattr__(self, attr):  # Only called if the attr wasn't found in the usual ways. Allows for Class-like lookup of stats.
        if attr not in _basic_fields:
            raise AttributeError("'Build' object has no attribute '{0}'".format(attr))

        return self.total(attr)


    def __getitem__(self, attr):  # Allows for dictionary-like lookup of stats.
        if attr not in _basic_fields:
            raise KeyError("'{0}'".format(attr))

        return self.total(attr)


    def __len__(self):  # Allows this class to be iterated over, where iterations return stat keywords
        return len(_basic_fields)

    @property
    def champion(self):
        """Returns the champion associated with this Build."""
        return self._champion


    @property
    def level(self):
        """Returns the level associated with this Build."""
        return self._level + 1


    @property
    def items(self):
        """Returns the level associated with this Build."""
        return self.item_set.list


    @property
    def masteries(self):
        """Returns a dictionary of (masteries, num_points) associated with this Build."""
        return self.mastery_page.dictionary


    @property
    def runes(self):
        """Returns a dictionary of (rune, num_selected) associated with this Build."""
        return self.rune_page.dictionary


    def _init_champions(all_champions=None):
        if not all_champions:
            all_champions = riotapi.get_champions()
            Build._champions = {champion.id: Champion(champion) for champion in all_champions}

        Build._champions_by_name = {champion.name: champion for _, champion in Build._champions.items()}


    def set_level(self, level):
        """@param level:  Sets the champion's level. An int between 1 and 18 is accepted."""

        if not 1 <= level <= 18:
            raise BuildError("'level' {0} must be between 1 and 18".format(level))
        self._level = level - 1


    def set_champion(self, champion):
        """@param champion:  Sets the champion for the Build. A name, id, or Cassiopeia Champion is accepted."""

        _champion = champion
        if isinstance(_champion, str):
            _champion = self._champions_by_name[_champion].id
        if not isinstance(_champion, int):
            _champion = _champion.id

        if _champion not in self._champions.keys():
            raise BuildError('Invalid champion name, id, or Cassiopeia Champion: {0}.'.format(champion))

        self._champion = self._champions[_champion]


    def set_items(self, item_set):
        """@param item_set:  Sets the items for the Build. Should be a list of item names, ids, or Cassiopeia Items."""

        if isinstance(item_set, list):
            item_set = ItemSet(item_set)

        self.item_set = item_set


    def set_masteries(self, mastery_page):
        """@param mastery_page:  Sets the mastery page for the Build. Should be a MasteryPage or dictionary."""

        if isinstance(mastery_page, dict):
            mastery_page = MasteryPage(mastery_page)

        self.mastery_page = mastery_page


    def set_runes(self, rune_page):
        """@param rune_page:  Sets the rune page for the Build. Should be a RunePage or dictionary."""

        if isinstance(rune_page, dict):
            rune_page = RunePage(rune_page)

        self.rune_page = rune_page


    def base(self, attr):
        """Returns the base value for the attribute."""

        flat, percent, per_level, percent_per_level, percent_base, percent_bonus = Build._get_object_stat(self._champion, attr)
        return Build._grow_stat(flat, per_level, self._level)


    def total(self, attr):
        """Returns the total value for the attribute."""

        # Note: DO NOT use self.bonus to calculate the total. self.bonus needs the total, calculated from scratch, to get its numbers correct
        total_flat = 0.0
        total_percent = 0.0
        total_per_level = 0.0
        total_percent_per_level = 0.0
        total_percent_base = 0.0
        total_percent_bonus = 0.0
        base = self.base(attr)
        for obj in self.item_set.list + self.rune_page.list + self.mastery_page.list:
            flat, percent, per_level, percent_per_level, percent_base, percent_bonus = Build._get_object_stat(obj, attr)
            total_flat += flat
            total_percent += percent
            total_per_level += per_level
            total_percent_per_level += percent_per_level
            total_percent_base += percent_base
            total_percent_bonus += percent_bonus
        total = ( (base * (1.0 + total_percent_base)) + total_flat + total_per_level*self._level ) * (1.0 + total_percent + total_percent_per_level*self._level)
        bonus = total - self.base(attr)
        total += total_percent_bonus * bonus
        return total


    def bonus(self, attr):
        """Returns the bonus value for the attribute."""
        return self.total(attr) - self.base(attr)


    def percent(self, attr):
        """Returns the percent (not including percent-per-level) value for the attribute."""

        total_percent = 0.0
        objects = self.item_set.list + self.rune_page.list + self.mastery_page.list
        for obj in objects:
            flat, percent, per_level, percent_per_level, percent_base, percent_bonus = Build._get_object_stat(obj, attr)
            total_percent += percent

        return total_percent


    def percent_bonus(self, attr):
        """Returns the percent bonus value for the attribute."""

        total_percent_bonus = 0.0
        objects = self.item_set.list + self.rune_page.list + self.mastery_page.list
        for obj in objects:
            flat, percent, per_level, percent_per_level, percent_base, percent_bonus = Build._get_object_stat(obj, attr)
            total_percent_bonus += percent_bonus

        return total_percent_bonus


    def percent_base(self, attr):
        """Returns the percent base value for the attribute."""

        total_percent_base = 0.0
        objects = self.item_set.list + self.rune_page.list + self.mastery_page.list
        for obj in objects:
            flat, percent, per_level, percent_per_level, percent_base, percent_bonus = Build._get_object_stat(obj, attr)
            total_percent_base += percent_base

        return total_percent_base


    def _grow_stat(base, per_level, level):
        """Grow a base stat based on the level of the champion."""

        return base + per_level*(7./400.*(level*level-1) + 267./400.*(level-1))


    def _get_object_stats(obj):
        """Parse the obj and return (flat, percent, per_level, percent_per_level) dictionaries of all stats in _basic_fields."""

        flat = defaultdict(float)
        percent = defaultdict(float)
        per_level = defaultdict(float)
        percent_per_level = defaultdict(float)
        percent_base = defaultdict(float)
        percent_bonus = defaultdict(float)
        for key in _basic_fields:
            flat[key] = getattr(obj, key, 0.0)
            percent[key] = getattr(obj, 'percent_'+key, 0.0)
            per_level[key] = getattr(obj, key+'_per_level', 0.0)
            percent_per_level[key] = getattr(obj, 'percent_'+key+'_per_level', 0.0)
            percent_base[key] = getattr(obj, 'percent_base_'+key, 0.0)
            percent_bonus[key] = getattr(obj, 'percent_bonus_'+key, 0.0)

        return flat, percent, per_level, percent_per_level, percent_base, percent_bonus


    def _get_object_stat(obj, key):
        """Parse the obj and return (flat, percent, per_level, percent_per_level) values (as floats) of the specified stat."""

        flat = getattr(obj, key, 0.0)
        percent = getattr(obj, 'percent_'+key, 0.0)
        per_level = getattr(obj, key+'_per_level', 0.0)
        percent_per_level = getattr(obj, 'percent_'+key+'_per_level', 0.0)
        percent_base = getattr(obj, 'percent_base_'+key, 0.0)
        percent_bonus = getattr(obj, 'percent_bonus_'+key, 0.0)

        return flat, percent, per_level, percent_per_level, percent_base, percent_bonus


    def get_stats_dictionary(self):
        """Returns a dictionary of the stats in this Build instance, including bonuses and bases."""

        d = {}
        for key in sorted(_basic_fields):
            d[key] = round(self.total(key), 3)
            d['bonus_'+key] = round(self.bonus(key), 3)
            d['base_'+key] = round(self.base(key), 3)

        return d


    def __str__(self):
        s = []
        for key in sorted(_basic_fields):
            s.append([key.replace('_', ' ').title(), self.base(key), self.bonus(key), self[key]])

        return tabulate(s, headers=['Stat', 'base', 'bonus', 'total'])


    def __repr__(self):
        return '<{0}.{1} object at {2}>'.format(self.__class__.__module__, self.__class__.__name__, hex(id(self)))

