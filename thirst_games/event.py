from random import random, choice
from typing import List

from thirst_games.constants import MAP, NARRATOR
from thirst_games.map import Map


class Event:
    def __init__(self, name: str, areas: List[str]):
        self.name = name
        self.areas = areas


class WildFire(Event):
    def __init__(self, _map: Map):
        max_p = max([len(place) for place in _map.areas.values()])
        areas = [key for key, value in _map.areas.items() if len(value) == max_p]
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
