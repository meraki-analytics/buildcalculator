from collections import Counter, defaultdict
from tabulate import tabulate
import json
import os
import math

from cassiopeia import riotapi
import cassiopeia.type.core.common

buildcalculator_director = os.path.dirname(os.path.realpath(__file__))

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
        self.tree = riot_mastery.tree


class Mastery(_Mastery):
    def __init__(self, mastery, points):
        self.id = mastery.id
        self.name = mastery.name
        self.points = points
        self.tree = mastery.tree
        for attr in _fields:
            setattr(self, attr, getattr(mastery, attr)[points])


class Rune(_BuildObject):
    pass


class Item(_BuildObject):
    def __init__(self, riot_obj, dictionary=None, default=0.0):
        super().__init__(riot_obj, dictionary, default)
        self.gold = riot_obj.gold
        self.components = riot_obj.components
        self.tags = riot_obj.tags

    @property
    def enchanted_name(self):
        return '{} ({})'.format(self.name, ', '.join(item.name for item in self.components))


class MasteryPage(defaultdict):
    _masteries_by_id = None
    _masteries_by_name = None


    def __init__(self, masteries=None, all_masteries=None):
        """@param masteries:  A dictionary of of (mastery_id, num_points) pairs. Defaults to an empty dictionary."""

        if not MasteryPage._masteries_by_id:
            MasteryPage._init_masteries(all_masteries)
        super().__init__(bool)
        self.update(masteries or {})
        self._check_page_viability()


    def _init_masteries(all_masteries):
        if not all_masteries:
            riotapi_masteries = {mastery.id: mastery for mastery in riotapi.get_masteries()}

            all_masteries = json.load(open(os.path.join(buildcalculator_director, 'masteries.json')))
            all_masteries = {int(id_): data for id_, data in all_masteries.items()}
            for id_, m in all_masteries.items():
                for key, values in m.items():
                    if key != 'tree' and key != 'name':
                        m[key] = {int(i): data for i, data in values.items()}
        else:
            MasteryPage._masteries_by_id = all_masteries

        MasteryPage._masteries_by_id = {id_: _Mastery(riotapi_masteries[id_], data) for id_, data in all_masteries.items()}
        MasteryPage._masteries_by_name = {mastery.name: mastery for _, mastery in MasteryPage._masteries_by_id.items()}


    def _check_page_viability(self):
        if not sum(mastery.points for mastery in self.keys()) <= 30:
            raise BuildError("A mastery page can have at most 30 points.")

        trees = {
            'Ferocity': [mastery for mastery in self.keys() if mastery.tree.value == 'Ferocity'],
            'Cunning':  [mastery for mastery in self.keys() if mastery.tree.value == 'Cunning'],
            'Resolve':  [mastery for mastery in self.keys() if mastery.tree.value == 'Resolve']
        }

        for tree, masteries in trees.items():
            # Make a dictionary that will contain the total points per row
            points = {i: 0 for i in range(1, 6+1)}
            for mastery in masteries:
                row = math.floor(mastery.id/10) % 10
                column = mastery.id % 10  # not needed
                points[row] += mastery.points
            # Loop through the rows and make sure things are correct
            for i in range(1, 6+1):
                # Make sure each row has <= 5 or 1 points in it
                if i % 2:  # odd row
                    assert points[i] <= 5
                else:  # even row
                    assert points[i] <= 1
                # If there is a point in the row, make sure all the ones before it have 5 or 1 in their rows
                if points[i] > 0:
                    for j in range(1, i+1):
                        if j % 2:  # odd row
                            assert points[j] == 5
                        else:  # even row
                            assert points[j] == 1


    def update(self, masteries):
        """@param masteries:  A dictionary of (mastery_id, num_points) or (mastery_name, num_points) pairs. Previous results are not overwritten."""

        if not (isinstance(masteries, dict) or isinstance(masteries, MasteryPage)):
            raise ValueError("'masteries' must be a dictionary or a MasteryPage")

        for m, p in masteries.items():
            self[Mastery(self._get_mastery(m), p)] = p


    @staticmethod
    def _get_mastery(mastery):
        if isinstance(mastery, str):
            mastery = MasteryPage._masteries_by_name[mastery]
        elif isinstance(mastery, int):
            mastery = MasteryPage._masteries_by_id[mastery]
        return MasteryPage._masteries_by_id[mastery.id]



class RunePage(defaultdict):
    _runes_by_id = None
    _runes_by_name = None


    def __init__(self, runes=None, all_runes=None):
        """@param runes:  A dictionary of of (rune_id, point) or (rune_name, point) key/value pairs. Defaults to an empty dictionary."""

        if not RunePage._runes_by_id:
            RunePage._init_runes(all_runes)
        super().__init__(bool)
        self.update(runes or {})


    def _init_runes(all_runes=None):
        if not all_runes:
            all_runes = {rune.id: rune for rune in riotapi.get_runes()}
            RunePage._runes_by_id = {id_: Rune(data) for id_, data in all_runes.items()}
        else:
            RunePage._runes_by_id = all_runes

        RunePage._runes_by_name = {rune.name: rune for _, rune in RunePage._runes_by_id.items()}


    def update(self, runes):
        """@param runes:  A dictionary of (rune_id, point) or (rune_name, point) pairs."""

        if not (isinstance(runes, dict) or isinstance(runes, RunePage)):
            raise ValueError("'runes' must be a dictionary or a RunePage")

        for r, p in runes.items():
            self[self._get_rune(r)] = p


    @staticmethod
    def _get_rune(rune):
        if isinstance(rune, str):
            rune = RunePage._runes_by_name[rune]
        elif isinstance(rune, int):
            rune = RunePage._runes_by_id[rune]
        assert isinstance(rune, Rune)
        return rune



class ItemSet(list):
    _items_by_id = None
    _items_by_name = None


    def __init__(self, items=None, all_items=None):
        """@param items:  A list of item IDs or item names. Defaults to an empty list."""

        if not ItemSet._items_by_id:
            ItemSet._init_items(all_items)

        super().__init__()
        self._trinket_index = None
        self.overwrite(items or [])


    def _init_items(all_items=None):
        if not all_items:
            all_items = riotapi.get_items()
            ItemSet._items_by_id = {item.id: Item(item) for item in all_items if item.maps[cassiopeia.type.core.common.Map.summoners_rift]}
        else:
            ItemSet._items_by_id = all_items

        ItemSet._items_by_name = {item.name: item for _, item in ItemSet._items_by_id.items()}


    @staticmethod
    def _get_item(item):
        if isinstance(item, str):
            if ' - ' in item:
                item = ItemSet.get_enchanted_item_by_name(item)
            else:
                item = ItemSet._items_by_name[item]
        elif isinstance(item, int):
            item = ItemSet._items_by_id[item]
        return item


    def remove(self, item):
        item = self._get_item(item)
        super().remove(item)


    def add(self, item):
        item = self._get_item(item)
        if 'Trinket' in item.tags:
            if self._trinket_index is not None:
                raise BuildError("An ItemSet can have only one trinket")
            else:
                super().append(item)
                self._trinket_index = len(self) - 1
        else:
            has_trinket = self._trinket_index is not None
            if len(self) > 6 + has_trinket:
                raise BuildError("An ItemSet can have at most 6 items (plus a trinket).")
            super().append(item)
    append = add


    def replace(self, item_before, item_after):
        item_before = self._get_item(item_before)
        item_after = self._get_item(item_after)
        self.remove(item_before)
        self.add(item_after)


    def overwrite(self, items):
        """@param items:  A list of item IDs or item names. Defaults to an empty dictionary. Any previous data is overwritten."""

        if not (isinstance(items, list) or isinstance(items, ItemSet)):
            raise ValueError("'items' must be a list or an ItemSet")

        self.clear()
        for item in items:
            self.add(item)


    @property
    def trinket(self):
        if self._trinket_index is None:
            return None
        else:
            return self[self._trinket_index]


    def get_enchanted_item_by_name(self, enchanted_item_name):
        """@param enchantment:  An enchantment to add to the itemset."""

        item_name, enchantment = enchanted_item_name.split(' - ')
        if isinstance(enchantment, str):
            item = self._items_by_name[item_name]
            for _, _item in self._items_by_id.items():
                if enchantment in _item.name:
                    if item.id in [component.id for component in _item.components]:
                        return _item
            else:
                raise ValueError("Enchantment {} not found!".format(enchantment))


    @property
    def cost(self):
        """Returns the total cost of the items."""
        return sum(item.gold.total for item in self)



class Build(object):
    _champions_by_id = None
    _champions_by_name = None


    def __init__(self, champion=None, level=1, item_set=None, rune_page=None, mastery_page=None):
        """@param champion:     A champion ID or name.
        @param level:        The champion's level.
        @param item_set:     A list of item IDs or item names. Defaults to an empty dictionary.
        @param rune_page:    The rune page or a dictionary of (rune_id/rune_name, num_runes) pairs.
        @param mastery_page: The rune page or a dictionary of (mastery_id/mastery_name, num_points) pairs.
        """

        if not Build._champions_by_id:
            Build._init_champions()

        if champion is None:
            raise TypeError("Build.__init__() missing 1 required positional argument: 'champion'")
        self.set_champion(champion)
        self.set_level(level)
        self.set_items(item_set or [])
        self.set_runes(rune_page or {})
        self.set_masteries(mastery_page or {})


    def __getattr__(self, attr):  # Only called if the attr wasn't found in the usual ways. Allows for Class-like lookup of stats.
        if 'percent_base_' in attr:
            attr = attr.replace('percent_base_', '')
            return self.percent_base(attr)
        if 'percent_bonus_' in attr:
            attr = attr.replace('percent_bonus_', '')
            return self.percent_bonus(attr)
        if 'percent_' in attr:
            attr = attr.replace('percent_', '')
            return self.percent(attr)
        if 'bonus_' in attr:
            attr = attr.replace('bonus_', '')
            return self.bonus(attr)
        if 'base_' in attr:
            attr = attr.replace('base_', '')
            return self.base(attr)
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
        """Returns the level associated with this build."""
        return self._level + 1


    @property
    def items(self):
        """Returns the item set associated with this build."""
        return self.item_set


    @property
    def masteries(self):
        """Returns the mastery page dictionary of (masteries, num_points) associated with this build."""
        return self.mastery_page


    @property
    def runes(self):
        """Returns the rune page dictionary of (rune, num_selected) associated with this build."""
        return self.rune_page


    @property
    def cost(self):
        """Returns the total cost of the items in the build."""
        return self.item_set.cost


    def _init_champions(all_champions=None):
        if not all_champions:
            all_champions = riotapi.get_champions()
            Build._champions_by_id = {champion.id: Champion(champion) for champion in all_champions}

        Build._champions_by_name = {champion.name: champion for _, champion in Build._champions_by_id.items()}


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

        if _champion not in self._champions_by_id.keys():
            raise BuildError('Invalid champion name, id, or Cassiopeia Champion: {0}.'.format(champion))

        self._champion = self._champions_by_id[_champion]


    def set_items(self, item_set):
        """@param item_set:  Sets the items for the build. Should be a list of item names, ids, or Cassiopeia Items."""

        if isinstance(item_set, list):
            item_set = ItemSet(item_set)

        self.item_set = item_set


    def set_masteries(self, mastery_page):
        """@param mastery_page:  Sets the mastery page for the build. Should be a MasteryPage or dictionary."""

        if isinstance(mastery_page, dict):
            mastery_page = MasteryPage(mastery_page)

        self.mastery_page = mastery_page


    def set_runes(self, rune_page):
        """@param rune_page:  Sets the rune page for the build. Should be a RunePage or dictionary."""

        if isinstance(rune_page, dict):
            rune_page = RunePage(rune_page)

        self.rune_page = rune_page


    def base(self, attr):
        """Returns the base value for the attribute."""

        flat, percent, per_level, percent_per_level, percent_base, percent_bonus = Build._get_object_stat(self._champion, attr)
        return Build._grow_stat(flat, per_level, self._level)


    @property
    def _objects(self):
        return self.item_set + [rune for rune, count in self.rune_page.items() for i in range(count)] + [mastery for mastery, points in self.mastery_page.items()]
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
        for obj in self._objects:
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
        for obj in self._objects:
            flat, percent, per_level, percent_per_level, percent_base, percent_bonus = Build._get_object_stat(obj, attr)
            total_percent += percent

        return total_percent


    def percent_bonus(self, attr):
        """Returns the percent bonus value for the attribute."""

        total_percent_bonus = 0.0
        for obj in self._objects:
            flat, percent, per_level, percent_per_level, percent_base, percent_bonus = Build._get_object_stat(obj, attr)
            total_percent_bonus += percent_bonus

        return total_percent_bonus


    def percent_base(self, attr):
        """Returns the percent base value for the attribute."""

        total_percent_base = 0.0
        for obj in self._objects:
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

