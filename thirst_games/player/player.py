from random import random
from typing import Dict

from thirst_games.constants import (
    NIGHT, STARTER, TRAPPED, START_AREA)
from thirst_games.context import Context
from thirst_games.narrator import format_list, Narrator
from thirst_games.player.fighter import Fighter
from thirst_games.traps import can_build_any_trap, build_any_trap


class Player(Fighter):
    def __init__(self, first_name: str, district: int, his='their'):
        Fighter.__init__(self, first_name, his)
        self.district = district
        self.relationships: Dict[Player, Relationship] = {}
        self.strategy = None
        self._destination = None

    def relationship(self, other_player):
        if other_player not in self.relationships:
            self.relationships[other_player] = Relationship()
        return self.relationships[other_player]

    def think(self):
        if self.sleep < 0:
            if self.map.players_count(self) > 1 and self.energy > self.move_cost:
                self.strategy = flee_strat
            else:
                self.strategy = hide_strat
        else:
            if Context().time == NIGHT:
                strats = night_strategies
            elif Context().time == STARTER:
                strats = start_strategies
            else:
                strats = morning_strategies
            strats.sort(key=lambda x: -x.pref(self) + random() * (1 - self.wisdom))
            self.strategy = strats[0]
            # if context['day'] == 1:
            #     Narrator().new([
            #         self.name, f': {[(round(s.pref(self, **context), 2), s.name) for s in strats]}'])

    def act(self):
        self.stop_running()
        Narrator().cut()
        if not self.busy:
            if Context().time == STARTER \
                    and self.current_area.name == START_AREA \
                    and self.map.players_count(self) == 1:
                strats = [loot_bag_strat, loot_weapon_strat, hide_strat]
                for s in [strat for strat in strats if strat.pref(self) > 0]:
                    s.apply(self)
            else:
                self.strategy.apply(self)
        Narrator().cut()
        self.strategy = None

    def fight(self, other_player):
        self.relationship(other_player).allied = False
        other_player.relationship(self).allied = False
        Fighter.fight(self, other_player)

    def should_go_get_drop(self):
        areas_by_value = {
            area: self.dangerosity() + self.estimate(self.map.loot(area)) - self.estimate_of_power(area)
            for area in self.map.area_names
        }
        filtered = [key for key, value in areas_by_value.items() if value > 0]
        if not len(filtered):
            self._destination = self.current_area
            return 0
        filtered.sort(key=lambda x: -areas_by_value[x])
        self._destination = filtered[0]
        # sp = ' '
        # self.map.test += f' {self.name}->{self._destination.split(sp)[-1]} '
        return areas_by_value[self._destination]

    def go_get_drop(self, **context):
        out = self.go_to(self._destination)
        if out is not None:
            Narrator().add([self.first_name, f'goes {out.to} to get loot'])
        else:
            Narrator().cut()
        if self.check_for_ambush_and_traps():
            return
        danger = self.estimate_of_power(self.current_area)
        seen_neighbors = [p for p in self.map.players(self) if self.can_see(p) and p != self]
        if danger > self.dangerosity():
            Narrator().add([self.first_name, 'sees', format_list([p.first_name for p in seen_neighbors])])
            self.flee(**context)
        elif danger > 0:
            self.attack_at_random()
        else:
            self.loot()


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
    lambda x: (len(x.wounds) + 1) *
                   (x.current_area != START_AREA or x.health > x.max_health / 2) *
                   (x.max_health - x.health / 2) *
                   (1 - min(x.energy, x.sleep)) /
                   x.map.players_count(x) + 0.1,
    lambda x: x.hide())
flee_strat = Strategy(
    'flee',
    lambda x: (x.energy > x.move_cost) * (
        x.estimate_of_power(x.current_area) / min(x.map.players_count(x), 6) - x.dangerosity()) + 0.1,
    lambda x: x.flee())
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
    lambda x: (x.energy - 0.2) * (2 - x.weapon.damage_mult) * (x.map.players_count(x) < 2),
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

start_strategies = [
    flee_strat, fight_strat, loot_bag_strat, loot_weapon_strat,
]

morning_strategies = [
    hide_strat, flee_strat, attack_strat, loot_strat, craft_strat_1, forage_strat, dine_strat, loot_bag_strat,
    hunt_player_strat, ambush_strat, go_get_drop, trap_strat, free_trap_strat, duel_strat,
]

night_strategies = [
    hide_strat, flee_strat, loot_strat, craft_strat_2, forage_strat, dine_strat, hunt_player_strat, ambush_strat,
    go_get_drop, trap_strat, free_trap_strat,
]
