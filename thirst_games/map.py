from typing import List, Dict, Union

from random import random, choice

from thirst_games.items import Weapon, Item, Food

START_AREA = 'the cornucopea'

food_values = {
    'roots': 0.2,
    'algae': 0.25,
    'mushrooms': 0.3,
    'berries': 0.3,
    'fruits': 0.4,
    'ration': 0.5,
}


class Positionable:
    current_area = ''


def get_area(area: Union[str, Positionable]) -> str:
    if isinstance(area, Positionable):
        return area.current_area
    if isinstance(area, str):
        return area
    raise ValueError(f'{area} is neither a string or a positionnable')


class Map:
    def __init__(self, size=4):
        self.nature = {
            START_AREA: {
                'food': []
            }, 'the ruins': {
                'food': ['roots']
            }, 'the forest': {
                'food': ['roots', 'fruits', 'mushrooms', 'berries']
            }, 'the plain': {
                'food': ['roots', 'berries']
            }, 'the rocks': {
                'food': []
            }, 'the jungle': {
                'food': ['roots', 'fruits']
            }, 'the river': {
                'food': ['roots', 'algae']
            }, 'the hill': {
                'food': ['roots']
            }
        }
        possible_parts_names = list(self.nature.keys())
        possible_parts_names.remove(START_AREA)
        possible_parts_names.sort(key=lambda x: random())
        self.areas = {area_name: [] for area_name in possible_parts_names[0:size-1]}
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
            Food('rations', 0.5 + random() / 2),
            Food('rations', 0.5 + random() / 2),
            Food('rations', 0.5 + random() / 2),
            Food('rations', 0.5 + random() / 2),
        ]

    def forage_potential(self, area):
        foods = self.nature[get_area(area)]['food']
        if len(foods):
            return max([food_values[name] for name in foods])
        return 0

    def get_forage(self, area):
        foods = self.nature[get_area(area)]['food']
        if not len(foods):
            return None
        food_name = choice(foods)
        return Food(food_name, random() * food_values[food_name])

    def weapons(self, area):
        return [e for e in self.loot[get_area(area)] if isinstance(e, Weapon)]

    def has_weapons(self, area):
        return len(self.weapons(get_area(area))) > 0

    def pick_weapon(self, area):
        area = get_area(area)
        if not self.has_weapons(area):
            return None
        w = choice(self.weapons(area))
        self.loot[area].remove(w)
        return w

    def pick_item(self, area):
        area = get_area(area)
        if not len(self.loot[area]):
            return None
        i = choice(self.loot[area])
        self.loot[area].remove(i)
        return i

    def remove_loot(self, item: Item, area: str):
        self.loot[area].remove(item)

    def add_loot(self, item: Item, area: str):
        self.loot[area].append(item)

    def add_player(self, element: Positionable):
        element.current_area = START_AREA
        self.areas[START_AREA].append(element)

    def remove_player(self, player):
        self.areas[player.current_area].remove(player)

    def move_player(self, player, new_area):
        if player.current_area == new_area:
            return 'nowhere'
        self.areas[player.current_area].remove(player)
        self.areas[new_area].append(player)
        player.current_area = new_area
        return new_area

    def neighbors_count(self, area):  # TODO: rename
        return len(self.areas[get_area(area)])

    def neighbors(self, element: Positionable):
        return [p for p in self.areas[element.current_area] if p != element]
