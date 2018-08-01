from random import random, choice, randint
from typing import List

from thirst_games.constants import MAP, NARRATOR, PLAYERS
from thirst_games.map import Map, START_AREA, random_bag


class Event:
    def __init__(self, name: str, areas: List[str]):
        self.name = name
        self.areas = areas

    def trigger(self, **context):
        raise NotImplementedError

    @classmethod
    def can_happen(cls, **context) -> bool:
        raise NotImplementedError


class WildFire(Event):
    def __init__(self, **context):
        _map = context[MAP]
        max_p = max([len(place) for key, place in _map.areas.items() if not _map.has_water(key)])
        areas = [key for key, value in _map.areas.items() if len(value) == max_p and not _map.has_water(key)]
        if max_p == 1:
            areas = [choice(areas)]
        Event.__init__(self, 'wildfire', areas)

    def trigger(self, **context):
        for area in self.areas:
            for p in context[MAP].areas[area]:
                context[NARRATOR].cut()
                if p.can_flee():
                    if p.be_damaged(0.3, weapon='fire', **context):
                        context[NARRATOR].new([p.name, 'fails', 'to escape the fire and dies', f'at {area}'])
                    else:
                        p.flee(**context)
                        context[NARRATOR].apply_stock()
                else:
                    context[NARRATOR].new([p.name, 'is', 'trapped', f'at {area}'])
                    if p.be_damaged(random() * 0.2 + 0.3, weapon='fire', **context):
                        context[NARRATOR].add(['and', 'the fire', 'kills', p.him])
                    else:
                        context[NARRATOR].apply_stock()

    @classmethod
    def can_happen(cls, **context) -> bool:
        return True


class DropEvent(Event):
    def __init__(self, **context):
        Event.__init__(self, 'drop', [START_AREA])

    def trigger(self, **context):
        nb_bags = randint(1, len(context[PLAYERS]) - 1)
        for i in range(nb_bags):
            context[MAP].add_loot(random_bag(), START_AREA)
        context[NARRATOR].new([nb_bags, 'bags', 'have been dropped', f'at {START_AREA}'])

    @classmethod
    def can_happen(cls, **context) -> bool:
        return context[MAP].neighbors_count(START_AREA) == 0
