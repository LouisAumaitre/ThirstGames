from random import random, choice, randint
from typing import List

from thirst_games.constants import SWORD, MACE, AXE
from thirst_games.context import Context
from thirst_games.items import Weapon, Bottle, Item, Food, Bag
from thirst_games.map import Map, START_AREA, Area
from thirst_games.narrator import Narrator, format_list


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
            self, name: str, it: str, stealth=0.6, weapon_name='',
            base_damage: float=0, extra_damage: float=0, dies='dies', trapped_means_dead=False,
    ):
        areas = self.available_areas()
        max_p = max([len(a.players) for a in areas])
        areas = [a for a in areas if len(a.players) == max_p]
        if max_p == 1:
            areas = [choice(areas)]
        Event.__init__(self, name, areas)
        self.stealth = stealth
        self.it = it
        self.weapon_name = weapon_name
        self.base_damage = base_damage
        self.extra_damage = extra_damage
        self.dies = dies
        self.trapped_means_dead = trapped_means_dead

    def trigger(self):
        for area in self.areas:
            for p in area.players:
                Narrator().cut()

                if p.can_flee():
                    if p.wisdom * random() > self.stealth:
                        Narrator().add([p.first_name, 'sees', self.it, 'coming'])
                        p.flee(filtered_areas=self.areas, stock=True)
                    elif p.be_damaged(self.base_damage, weapon=self.weapon_name):
                        Narrator().new([p.name, 'fails', 'to escape', self.it, 'and', self.dies, area.at])
                    else:
                        p.flee(panic=True, drop_verb='loses', filtered_areas=self.areas, stock=True)
                else:
                    Narrator().new([p.name, 'is', 'trapped', area.at])

                if p.current_area not in self.areas:
                    Narrator().apply_stock()
                    continue  # successful escape

                Narrator().clear_stock()
                if self.trapped_means_dead:
                    p.be_damaged(1)
                    Narrator().add([p.name, 'is', 'swipped', 'by', self.it, area.at, 'and', self.dies])
                elif p.be_damaged(random() * self.extra_damage + self.base_damage, weapon=self.weapon_name):
                    Narrator().add(['and', self.dies])
                else:
                    Narrator().apply_stock()
                if not len(Narrator().current_sentence):  # error
                    Narrator().add([p.name, 'escaped', self.it, 'and is', p.current_area.at])
            Narrator().clear_stock()
            area.loot.clear()

    @classmethod
    def can_happen(cls) -> bool:
        return len(cls.available_areas()) > 0

    @classmethod
    def available_areas(cls) -> List[Area]:
        areas = [a for a in Map().areas if len(a.players)]
        if cls.water == -1:
            areas = [a for a in areas if not a.has_water]
        if cls.water == 1:
            areas = [a for a in areas if not a.has_water]
        return areas


class WildFire(DamageEvent):
    water = -1

    def __init__(self):
        DamageEvent.__init__(
            self, 'wildfire', 'the fire',
            weapon_name='fire', dies='burns to death',
            base_damage=0.3, extra_damage=0.2,
        )


class Flood(DamageEvent):
    water = 1

    def __init__(self):
        DamageEvent.__init__(
            self, 'flood', 'the flood', dies='drowns', trapped_means_dead=True
        )


class AcidGas(DamageEvent):
    def __init__(self):
        DamageEvent.__init__(
            self, 'acid cloud', 'the acid',
            weapon_name='acid', dies='melts into a puddle of blood',
            base_damage=0.2, trapped_means_dead=True,
        )


class Wasps(DamageEvent):
    def __init__(self):
        DamageEvent.__init__(
            self, 'killer wasps', 'the wasps',
            weapon_name='acid', dies='dies from anaphylactic shock',
            base_damage=0.2, extra_damage=0.4,
        )


class Beasts(DamageEvent):
    def __init__(self):
        DamageEvent.__init__(
            self, choice(['dogs', 'killer monkeys']), 'the beasts',
            weapon_name='teeth', dies='is eaten alive',
            base_damage=0.2, extra_damage=0.4,
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
