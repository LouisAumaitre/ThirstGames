from typing import List

from copy import copy
from random import random, choice, randint

from thirst_games.abstract.items import Weapon, Bottle, Item, Bag
from thirst_games.constants import SWORD, MACE, AXE
from thirst_games.context import Context
from thirst_games.map import Map, START_AREA, Area
from thirst_games.narrator import Narrator, format_list


# TODO: sometimes events don't seem to affect everyone
from thirst_games.poison import Food


class Event:
    def __init__(self, name: str, areas: List[Area]):
        self.name = name
        self.areas = areas

    def trigger(self):
        raise NotImplementedError

    @classmethod
    def can_happen(cls) -> bool:
        raise NotImplementedError


class DamageEvent(Event):
    water = 0

    def __init__(
            self, name: str, it: str, stealth=0.6, weapon_name='', remove_loot=False,
            base_damage: float=0, extra_damage: float=0, dies='dies', trapped_means_dead=False,
    ):
        areas = self.available_areas()
        areas.sort(key=lambda x: -len(x.players))
        picked_areas = [areas.pop(0)]
        while len(areas) > Context().player_count // 4:
            picked_areas.append(areas.pop(0))
            if len(areas) < 2:
                break
        Event.__init__(self, name, picked_areas)
        self.stealth = stealth
        self.it = it
        self.weapon_name = weapon_name
        self.base_damage = base_damage
        self.extra_damage = extra_damage
        self.dies = dies
        self.trapped_means_dead = trapped_means_dead
        self.remove_loot = remove_loot

    def trigger(self):
        Context().forbidden_areas.extend(self.areas)
        saw_it_coming = []
        warned = []
        # Narrator().add(['should trigger for', [p.name for a in self.areas for p in a.players]])
        for area in self.areas:
            for p_e in Context().playing_entities_at(area):
                for p in p_e.players:
                    if p.wisdom * random() > self.stealth:
                        saw_it_coming.append(p.name)
                        warned.extend(p_e.players)
                        break
        if len(saw_it_coming):
            Narrator().new([
                format_list(saw_it_coming), 'see' if len(saw_it_coming) > 1 else 'sees', self.it, 'coming'
            ])
        for area in self.areas:
            area_players = copy(area.players)
            for p in area_players:
                Narrator().cut()

                if p.can_flee():
                    if p in warned:
                        p.flee()
                        if p.current_area in self.areas:
                            Narrator().new([
                                'error:', 'forbidden:', Context().forbidden_areas, p.name, p.current_area.at])
                            Map().test = 'SHIT'
                    elif p.be_damaged(self.base_damage, weapon=self.weapon_name):
                        Narrator().new([p.name, 'fails', 'to escape', self.it, 'and', self.dies, area.at])
                    else:
                        Narrator().apply_stock()
                        p.flee(panic=True, drop_verb='loses')
                    continue  # successful escape
                Narrator().new([p.name, 'is', 'trapped', area.at])
                if self.trapped_means_dead:
                    p.be_damaged(1)
                    Narrator().add([p.name, 'is', 'swiped', 'by', self.it, area.at, 'and', self.dies])
                elif p.be_damaged(random() * self.extra_damage + self.base_damage, weapon=self.weapon_name):
                    Narrator().add(['and', self.dies])
                else:
                    Narrator().apply_stock()
                if not len(Narrator().current_sentence):  # error
                    Narrator().add([p.name, 'escaped', self.it, 'and is', p.current_area.at])
            Narrator().clear_stock()
            if self.remove_loot:
                area.loot.clear()

    @classmethod
    def can_happen(cls) -> bool:
        return len([a for a in cls.available_areas() if len(a.players)]) > 0

    @classmethod
    def available_areas(cls) -> List[Area]:
        areas = copy(Map().areas)
        if cls.water == -1:
            areas = [a for a in areas if not a.has_water]
        if cls.water == 1:
            areas = [a for a in areas if a.has_water]
        return areas


class WildFire(DamageEvent):
    water = -1

    def __init__(self):
        DamageEvent.__init__(
            self, 'wildfire', 'the fire',
            weapon_name='fire', dies='burns to death',
            base_damage=0.3, extra_damage=0.2, remove_loot=True,
        )


class Flood(DamageEvent):
    water = 1

    def __init__(self):
        DamageEvent.__init__(
            self, 'flood', 'the flood', dies='drowns', trapped_means_dead=True, remove_loot=True,
        )


class AcidGas(DamageEvent):
    def __init__(self):
        DamageEvent.__init__(
            self, 'acid cloud', 'the acid',
            weapon_name='acid', dies='melts into a puddle of blood',
            base_damage=0.2, trapped_means_dead=True, stealth=0.7,
        )


class Wasps(DamageEvent):
    def __init__(self):
        DamageEvent.__init__(
            self, 'killer wasps', 'the wasps',
            weapon_name='acid', dies='dies from anaphylactic shock',
            base_damage=0.2, extra_damage=0.4, stealth=0.8,
        )


class Beasts(DamageEvent):
    def __init__(self):
        DamageEvent.__init__(
            self, choice(['dogs', 'killer monkeys']), 'the beasts',
            weapon_name='teeth', dies='is eaten alive',
            base_damage=0.2, extra_damage=0.4, stealth=0.7,
        )


class DropEvent(Event):
    def __init__(self):
        possible_areas = [area for area in Map().areas if not len(area.players)]
        if START_AREA in possible_areas:
            area = Map().get_area(START_AREA)
        else:
            area = choice(possible_areas)
        Event.__init__(self, 'drop', [area])

    def trigger(self):
        possible_loots = [
            Food(choice(['ration', 'food can', 'energy bar']), 0.75),
            Food(choice(['ration', 'food can', 'energy bar']), 0.50),
            Food(choice(['ration', 'food can', 'energy bar']), 0.25),
            Item('bandages'), Item('iodine'), Item('antidote'), Bottle(1),
            Weapon(choice([SWORD, AXE, MACE]), 2 + random())
        ]
        possible_loots = [i for i in possible_loots if sum(p.estimate(i) for p in Context().alive_players)]
        possible_loots.sort(key=lambda x: -sum(p.estimate(x) for p in Context().alive_players))
        area = self.areas[0]
        nb_bags = randint(1, len(Context().alive_players) - 1)
        while nb_bags > len(possible_loots):
            possible_loots.extend(possible_loots)
        bags = []
        for i in range(nb_bags):
            bags.append(Bag([possible_loots[i], possible_loots[-(i + 1)]]))
        for bag in bags:
            Map().add_loot(bag, area)
        verb = 'have' if nb_bags > 1 else 'has'
        Narrator().new([nb_bags, 'bag' + ('s' if nb_bags > 1 else ''), verb, 'been dropped', area.at])
        Narrator().new([
            'The bag' + ('s' if nb_bags > 1 else ''), 'contain' + ('s' if nb_bags == 1 else ''),
            format_list([i.name for b in bags for i in b.content])])

    @classmethod
    def can_happen(cls) -> bool:
        # needs an empty area
        return len([area for area in Map().areas if not len(area.players)]) > 0
