from random import random
from typing import Dict, List

from thirst_games.constants import (NIGHT, STARTER, TRAPPED, START_AREA)
from thirst_games.context import Context
from thirst_games.map import Map, Area
from thirst_games.narrator import format_list, Narrator
from thirst_games.player.carrier import Carrier
from thirst_games.player.fighter import Fighter
from thirst_games.traps import can_build_any_trap, build_any_trap


class Player(Fighter):
    def __init__(self, first_name: str, district: int, his='their') -> None:
        Fighter.__init__(self, first_name, his)
        self.district = district
        self.relationships: Dict[str, Relationship] = {}
        self.strategy = None
        self.acted = True

    def relationship(self, other_player):
        if other_player.name not in self.relationships:
            self.relationships[other_player.name] = Relationship()
        return self.relationships[other_player.name]

    def allies(self):
        return [p for p in Context().alive_players if self.relationship(p).allied]

    def present_allies(self):
        return [
            p for p in Context().alive_players if self.relationship(p).allied and self.current_area == p.current_area
        ]

    def busy_allies(self):
        return [p for p in Context().alive_players if self.relationship(p).allied and p.busy]

    def enemies(self, area: Area) -> List[Carrier]:
        return [p for p in area.players if p != self and not self.relationship(p).allied]

    def current_group(self):
        return [*[p for p in self.present_allies() if not p.busy], self]

    def think(self):
        if self.strategy is not None or self.acted:
            return
        allies = self.present_allies()
        if len(allies):
            strats = self._think()
            for a in allies:
                for s, v in a._think().items():
                    strats[s] = strats.get(s, 0) + v
        else:
            strats = self._think()
        self.strategy = [s for s, v in strats.items() if v == max(strats.values())][0]
        for a in allies:
            print(f'{self.name}&{a.name}:{self.strategy.name}')
            a.strategy = self.strategy

    def _think(self) -> dict:
        if self.sleep < 0:
            if self.map.players_count(self) > 1 and self.energy > self.move_cost:
                strats = flee_strats()
            else:
                return {hide_strat: 1}
        else:
            if Context().time == NIGHT:
                strats = night_strategies()
            elif Context().time == STARTER:
                strats = start_strategies()
            else:
                strats = morning_strategies()
        # strats.sort(key=lambda x: -x.pref(self) + random() * (1 - self.wisdom))
        return {s: s.pref(self) + random() * (1 - self.wisdom) for s in strats}
        # if self.strategy == go_get_drop:
        #     Narrator().new([
        #         self.name, f': {[(round(s.pref(self), 2), s.name) for s in strats]}'])

    def _flee_value(self, area):
        return Fighter._flee_value(self, area) + 30 * len([a for a in self.allies() if a in area.players])

    def _pursue_value(self, area):
        return Fighter._flee_value(self, area) + 30 * len([a for a in self.allies() if a in area.players])

    def act(self):
        Narrator().cut()
        for p in self.current_group():
            p._act()
            Narrator().cut()

    def _act(self):
        if self.acted:
            return
        self.stop_running()
        if self.energy < 0:
            self.go_to_sleep()
        elif not self.busy:
            if Context().time == STARTER \
                    and self.current_area.name == START_AREA \
                    and self.map.players_count(self) == 1:
                strats = [loot_bag_strat, loot_weapon_strat, hide_strat]
                for s in [strat for strat in strats if strat.pref(self) > 0]:
                    s.apply(self)
            else:
                self.strategy.apply(self)
        self.strategy = None
        self.acted = True

    def fight(self, other_player):
        self.relationship(other_player).allied = False
        other_player.relationship(self).allied = False
        Fighter.fight(self, other_player)

    def should_go_get_drop(self):
        areas_by_value = {
            area: self.dangerosity() + self.estimate(self.map.loot(area)) - self.estimate_of_danger(area)
            for area in self.map.area_names
        }
        filtered = [key for key, value in areas_by_value.items() if value > 0]
        if not len(filtered):
            self.destination = self.current_area
            return 0
        filtered.sort(key=lambda x: -areas_by_value[x])
        self.destination = filtered[0]
        # sp = ' '
        # self.map.test += f' {self.name}->{self._destination.split(sp)[-1]} '
        return areas_by_value[self.destination] * min([
            random(), 3 / Context().player_count])

    def go_get_drop(self):
        out = self.go_to(self.destination)
        if out is not None:
            Narrator().add([self.first_name, f'goes {out.to} to get loot'])
        else:
            Narrator().cut()
        if self.check_for_ambush_and_traps():
            return
        seen_neighbors = [p for p in self.map.potential_players(self) if self.can_see(p) and p != self]
        free_neighbors = [p for p in seen_neighbors if p.current_area == self.current_area and not p.busy]
        potential_danger = sum([p.dangerosity() for p in seen_neighbors])
        actual_danger = sum([p.dangerosity() for p in free_neighbors])

        if potential_danger > self.dangerosity() and potential_danger > self.courage():
            Narrator().add([self.first_name, 'sees', format_list([p.first_name for p in seen_neighbors])])
            self.flee()
        elif actual_danger > self.dangerosity() and actual_danger > self.courage():
            Narrator().add([self.first_name, 'sees', format_list([p.first_name for p in free_neighbors])])
            self.flee()
        elif actual_danger > 0:  # enemy present -> fight them
            Narrator().cut()
            self.attack_at_random()
        elif potential_danger > 0 and actual_danger == 0:  # enemy busy but incoming
            if self.dangerosity() > potential_danger:  # attack before the other(s) arrive
                Narrator().cut()
                self.attack_at_random()
            else:  # loot and go/get your load and hit the road
                Narrator().add([self.first_name, 'avoids', format_list([p.first_name for p in seen_neighbors])])
                self.loot(take_a_break=False)
                self.flee()
        else:  # servez-vous
            self.loot()
        if len(Narrator().current_sentence) == 0:
            Narrator().add([
                self.name, f'potential_danger={potential_danger}', f'actual_danger={actual_danger}',
                f'dangerosity={self.dangerosity()}', f'courage={self.courage()}',
            ])


class Relationship:
    def __init__(self):
        self.friendship = 0
        self.allied = False


class Strategy:
    def __init__(self, name, pref, action):
        self.name = name
        self.pref = pref
        self.action = action

    def apply(self, player):
        out = self.action(player)
        if isinstance(out, str):
            print(f'{player.first_name} {out}')


hide_strat = Strategy(
    'hide',
    lambda x: max(
        [max([
            len(x.wounds) * 3, x.max_health - x.health,
            1 - x.energy, 1 - x.sleep,
            x.thirst if x.current_area.has_water else 0
        ]) * (
            x.current_area != START_AREA or x.health > x.max_health / 2
        ) * (
            x.max_health - x.health / 2
        ) / x.map.players_count(x), 0.1]),
    lambda x: x.hide())


def flee_strats():
    return [Strategy(
        f'flee to {area.name}',
        lambda x: x._flee_value(area) / 30,
        lambda x: x.flee()
    ) for area in Map().areas]


attack_strat = Strategy(
    'attack',
    lambda x: x.health * min(x.energy, x.stomach, x.sleep) *
                   x.weapon.damage_mult / Context().player_count,  # * (len(c[PLAYERS]) < 4),
    lambda x: x.attack_at_random())
ambush_strat = Strategy(
    'ambush',
    lambda x: x.health * min(x.energy, x.stomach, x.sleep) * x.weapon.damage_mult * (x.map.players_count(x) == 1),
    lambda x: x.set_up_ambush())
hunt_player_strat = Strategy(
    'hunt player',
    lambda x: x.health * x.weapon.damage_mult * (Context().player_count < 4),
    lambda x: x.attack_at_random())
fight_strat = Strategy(
    'fight',
    lambda x: x.health * sum([x.dangerosity() > n.dangerosity() * 1.2 for n in x.map.players(x)]),
    lambda x: x.attack_at_random())
duel_strat = Strategy(
    'duel',
    lambda x: (Context().player_count == 2) * sum(
        [x.dangerosity() > n.dangerosity() * 1.2 for n in x.map.players(x)]),
    lambda x: x.attack_at_random())
loot_strat = Strategy(
    'loot',
    lambda x: (x.energy - x.move_cost) * (2 if x.weapon.damage_mult == 1 else 0.2) * x.estimate(x.map.loot(x)),
    lambda x: x.loot())
go_get_drop = Strategy('go get loot', lambda x: x.should_go_get_drop(), lambda x: x.go_get_drop())
loot_bag_strat = Strategy(
    'loot bag',
    lambda x: x.weapon.damage_mult * x.map.has_bags(x) * (x.bag is None),
    lambda x: x.loot_bag())
loot_weapon_strat = Strategy(
    'loot weapon',
    lambda x: x.estimate(x.map.weapons(x)),
    lambda x: x.loot_weapon())
forage_strat = Strategy(
    'forage',
    lambda x: x.hunger * x.map.forage_potential(x) / x.map.players_count(x),
    lambda x: x.forage())
dine_strat = Strategy(
    'dine',
    lambda x: x.hunger * x.has_food / x.map.players_count(x),
    lambda x: x.dine())
craft_strat_1 = Strategy(
    'craft',
    lambda x: (2 - x.weapon.damage_mult) * (1 / x.map.players_count(x)),
    lambda x: x.craft())
craft_strat_2 = Strategy(
    'craft',
    lambda x: (x.energy - 0.2) * (x.weapon.damage_mult < 2) * (2 - x.weapon.damage_mult) / x.map.players_count(x),
    lambda x: x.craft())
trap_strat = Strategy(
    'build trap',
    lambda x: (x.energy - 0.2) * (x.map.players_count(x) < 2) * (can_build_any_trap(x)),
    lambda x: build_any_trap(x))
free_trap_strat = Strategy(
    'free from trap',
    lambda x: 1000 * (TRAPPED in x.status),
    lambda x: x.free_from_trap())


def start_strategies():
    return [
        *flee_strats(), fight_strat, loot_bag_strat, loot_weapon_strat,
    ]


def morning_strategies():
    return [
        hide_strat, *flee_strats(), attack_strat, loot_strat, craft_strat_1, forage_strat, dine_strat, loot_bag_strat,
        hunt_player_strat, ambush_strat, go_get_drop, trap_strat, free_trap_strat, duel_strat,
    ]


def night_strategies():
    return [
        hide_strat, *flee_strats(), loot_strat, craft_strat_2, forage_strat, dine_strat, hunt_player_strat,
        ambush_strat, go_get_drop, trap_strat, free_trap_strat,
    ]
