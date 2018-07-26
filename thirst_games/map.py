from typing import List, Dict

from random import random, choice

from thirst_games.items import Weapon, Item

START_AREA = 'the cornucopea'


class Map:
    def __init__(self, size=4):
        possible_parts = [
            'the ruins', 'the forest', 'the plain', 'the rocks', 'the jungle', 'the river', 'the hill'
        ]
        possible_parts.sort(key=lambda x: random())
        self.areas = {area_name: [] for area_name in possible_parts[0:size-1]}
        self.areas[START_AREA] = []
        self.loot: Dict[str, List[Item]] = {area_name: [] for area_name in self.areas.keys()}
        self.loot[START_AREA] = [
            Weapon('sword', 2.5 + random()),
            Weapon('sword', 2.5 + random()),
            Weapon('trident', 2 + random()),
            Weapon('axe', 2.5 + random()),
            Weapon('knife', 1 + random()),
            Weapon('knife', 1 + random()),
            Weapon('knife', 1 + random()),
            Weapon('knife', 1 + random()),
        ]

    def weapons(self, area):
        return [e for e in self.loot[area] if isinstance(e, Weapon)]

    def has_weapons(self, area):
        return len(self.weapons(area)) > 0

    def pick_weapon(self, area):
        if not self.has_weapons(area):
            return None
        w = choice(self.weapons(area))
        self.loot[area].remove(w)
        return w

    def remove_loot(self, item: Item, area: str):
        self.loot[area].remove(item)

    def add_loot(self, item: Item, area: str):
        self.loot[area].append(item)

    def add_player(self, player):
        player.current_area = START_AREA
        self.areas[START_AREA].append(player)

    def remove_player(self, player):
        self.areas[player.current_area].remove(player)

    def move_player(self, player, new_area):
        if player.current_area == new_area:
            return 'nowhere'
        self.areas[player.current_area].remove(player)
        self.areas[new_area].append(player)
        player.current_area = new_area
        return new_area

    def neighbors_count(self, player):
        return len(self.areas[player.current_area])

    def neighbors(self, player):
        return [p for p in self.areas[player.current_area] if p != player]
