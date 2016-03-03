import sys
import os

from buildcalculator import MasteryPage, RunePage, ItemSet, Build
from cassiopeia import riotapi


def Jinx():
    mp = {'Fury':5, 'Feast':1, 'Vampirism':5, 'Bounty Hunter':1, 'Battering Blows':5, 'Fervor of Battle':1,
          'Wanderer':5, 'Secret Stash':1, 'Merciless':5, 'Dangerous Game':1}
    mp = MasteryPage(mp)  # Optional

    rp = {'Greater Mark of Attack Damage':9, 'Greater Seal of Armor':9, 'Greater Glyph of Magic Resist':9, 'Greater Quintessence of Attack Speed':2, 'Greater Quintessence of Attack Damage':1}
    rp = RunePage(rp)  # Optional

    items = ['Infinity Edge', "Berserker's Greaves", "Lord Dominik's Regards", 'The Bloodthirster', 'Mercurial Scimitar', "Banshee's Veil"]
    items = ItemSet(items)  # Optional

    build = Build(champion='Jinx', level=18, item_set=items, rune_page=rp, mastery_page=mp)
    # The below would work as well
    #build = Build(champion='Jinx')
    #build.set_level(18)
    #build.set_items(items)
    #build.set_masteries(mp)
    #build.set_runes(rp)
    return build


def Annie():
    mp = {'Sorcery':5, 'Double Edged Sword':1, 'Natural Talent':5, 'Oppressor':1,
          'Wanderer':5, 'Secret Stash':1, 'Merciless':5, 'Dangerous Game':1, 'Precision':5, "Thunderlord's Decree":1}

    rp = {'Greater Mark of Hybrid Penetration':9, 'Greater Seal of Armor':9, 'Greater Glyph of Magic Resist':9, 'Greater Quintessence of Ability Power':3}

    items = ["Sorcerer's Shoes", 'Morellonomicon', "Rabadon's Deathcap"]

    build = Build(champion='Annie', level=10, item_set=items, rune_page=rp, mastery_page=mp)
    return build


def Amumu():
    mp = {'Sorcery':5, 'Double Edged Sword':1, 'Natural Talent':5, 'Oppressor':1,
          'Wanderer':5, 'Secret Stash':1, 'Merciless':5, 'Dangerous Game':1, 'Precision':5, "Thunderlord's Decree":1}

    rp = {'Greater Mark of Magic Penetration':9, 'Greater Seal of Armor':9, 'Greater Glyph of Cooldown Reduction':6, 'Greater Glyph of Magic Resist':3, 'Greater Quintessence of Ability Power':3}

    # Enchantments should follow the item name, separated by ' - ' (note the spaces around the dash)
    items = ["Stalker's Blade - Cinderhulk", "Mercury's Treads - Alacrity", "Dead Man's Plate", "Banshee's Veil", 'Abyssal Scepter', "Liandry's Torment"]

    build = Build(champion='Amumu', level=18, item_set=items, rune_page=rp, mastery_page=mp)
    return build


def Thresh():
    mp = {6311: 5, 6322: 1, 6332: 5, 6342: 1, 6211: 5, 6223: 1, 6232: 5, 6241: 1, 6251: 5, 6263: 1}
    rp = {5317: 9, 5245: 9, 5289: 9, 5296: 3}
    items = [3111, 3097, 1011]
    build = Build(champion=412, level=5, item_set=items, rune_page=rp, mastery_page=mp)
    return build

def main():
    riotapi.set_api_key(os.environ['DEV_KEY'])
    riotapi.print_calls(True)
    riotapi.set_region('NA')

    try:
        champ = sys.argv[1].lower()
    except IndexError:
        champ = 'jinx'

    if champ == 'jinx':
        build = Jinx()
    elif champ == 'annie':
        build = Annie()
    elif champ == 'amumu':
        build = Amumu()
    elif champ == 'thresh':
        build = Thresh()
    else:
        build = Jinx()

    print()
    print(build.__repr__())
    print()
    # These are different ways to access stats
    print('Total armor: ', build.armor)
    print('Total armor: ', build['armor'])
    print('Total armor: ', build.total('armor'))
    print('Base armor: ', build.base('armor'))
    print('Bonus armor: ', build.bonus('armor'))
    print()
    print(build)

    print()
    print('Champion: {0}'.format(build.champion))
    print('Level: {0}'.format(build.level))
    print('Items: {0}'.format([item.name for item in build.items]))
    print('Runes: {0}'.format({rune.name: points for rune, points in build.runes.items()}))
    print('Masteries: {0}'.format({mastery.name: points for mastery, points in build.masteries.items()}))


if __name__ == '__main__':
    main()
