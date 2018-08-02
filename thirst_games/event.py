from random import random, choice, randint
from typing import List

from thirst_games.context import Context
from thirst_games.map import Map, START_AREA, random_bag, Area
from thirst_games.narrator import Narrator


class Event:
    def __init__(self, name: str, areas: List[Area]):
        self.name = name
        self.areas = areas

    def trigger(self):
        raise NotImplementedError

    @classmethod
    def can_happen(cls) -> bool:
        raise NotImplementedError


class WildFire(Event):
    def __init__(self):
        _map = Map()
        max_p = max([len(area.players) for area in _map.areas if not area.has_water])
        areas = [area for area in _map.areas if len(area.players) == max_p and not area.has_water]
        if max_p == 1:
            areas = [choice(areas)]
        Event.__init__(self, 'wildfire', areas)

    def trigger(self):
        for area in self.areas:
            for p in area.players:
                Narrator().cut()
                if p.can_flee():
                    if p.be_damaged(0.3, weapon='fire'):
                        Narrator().new([p.name, 'fails', 'to escape the fire and dies', f'at {area}'])
                    else:
                        p.flee()
                        Narrator().apply_stock()
                else:
                    Narrator().new([p.name, 'is', 'trapped', f'at {area}'])
                    if p.be_damaged(random() * 0.2 + 0.3, weapon='fire'):
                        Narrator().add(['and', 'the fire', 'kills', p.him])
                    else:
                        Narrator().apply_stock()

    @classmethod
    def can_happen(cls) -> bool:
        # needs a place with players and no water
        return len([area for area in Map().areas if not area.has_water and len(area.players)]) > 0


class DropEvent(Event):
    def __init__(self):
        possible_areas = [area for area in Map().areas if not len(area.players)]
        if START_AREA in possible_areas:
            area = Map().get_area(START_AREA)
        else:
            area = choice(possible_areas)
        Event.__init__(self, 'drop', [area])

    def trigger(self):
        area = self.areas[0]
        nb_bags = randint(1, len(Context().alive_players) - 1)
        for i in range(nb_bags):
            Map().add_loot(random_bag(), area)
        verb = 'have' if nb_bags > 1 else 'has'
        Narrator().new([nb_bags, 'bag' + ('s' if nb_bags > 1 else ''), verb, 'been dropped', f'at {area}'])

    @classmethod
    def can_happen(cls) -> bool:
        # needs an empty area
        return len([area for area in Map().areas if not len(area.players)]) > 0
