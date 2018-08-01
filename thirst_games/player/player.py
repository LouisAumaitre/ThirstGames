from random import random
from typing import Dict

from thirst_games.constants import (
    MAP, PLAYERS, TIME, NARRATOR, NIGHT, STARTER, TRAPPED,
)
from thirst_games.map import START_AREA
from thirst_games.narrator import format_list
from thirst_games.player.fighter import Fighter
from thirst_games.traps import can_build_any_trap, build_any_trap


class Player(Fighter):
    def __init__(self, first_name: str, district: int, his='their'):
        Fighter.__init__(self, first_name, his)
        self.district = district
        self.relationships: Dict[Player, Relationship] = {}
        self.strategy = None

    def relationship(self, other_player):
        if other_player not in self.relationships:
            self.relationships[other_player] = Relationship()
        return self.relationships[other_player]

    def think(self, **context):
        if self.sleep < 0:
            if context[MAP].neighbors_count(self) > 1 and self.energy > self.move_cost:
                self.strategy = flee_strat
            else:
                self.strategy = hide_strat
        else:
            if context[TIME] == NIGHT:
                strats = night_strategies
            elif context[TIME] == STARTER:
                strats = start_strategies
            else:
                strats = morning_strategies
            strats.sort(key=lambda x: -x.pref(self, **context) + random() * (1 - self.wisdom))
            self.strategy = strats[0]
            if context['day'] == 1:
                context[NARRATOR].new([
                    self.name, f': {[(round(s.pref(self, **context), 2), s.name) for s in strats]}'])

    def act(self, **context):
        self.stop_running()
        context[NARRATOR].cut()
        if not self.busy:
            if context[TIME] == STARTER and self.current_area == START_AREA and context[MAP].neighbors_count(self) == 1:
                strats = [loot_bag_strat, loot_weapon_strat, hide_strat]
                for s in [strat for strat in strats if strat.pref(self, **context) > 0]:
                    s.apply(self, **context)
            else:
                self.strategy.apply(self, **context)
        context[NARRATOR].cut()
        self.strategy = None

    def fight(self, other_player, **context):
        self.relationship(other_player).allied = False
        other_player.relationship(self).allied = False
        Fighter.fight(self, other_player, **context)

    def loot_cornucopia(self, **context):
        out = self.go_to(START_AREA, **context)
        if out is not None:
            context[NARRATOR].add([self.first_name, f'goes to {START_AREA} to get loot'])
        if self.check_for_ambush_and_traps(**context):
            return
        neighbors = context[MAP].neighbors(self)
        if not len(neighbors):
            self.loot(**context)
            return
        seen_neighbors = [p for p in neighbors if self.can_see(p)]
        if sum([p.dangerosity(**context) for p in seen_neighbors]) > self.dangerosity(**context):
            context[NARRATOR].add([self.first_name, 'sees', format_list([p.first_name for p in neighbors])])
            self.flee(**context)
        elif len(seen_neighbors):
            self.attack_at_random(**context)
        else:
            self.loot(**context)


class Relationship:
    def __init__(self):
        self.friendship = 0
        self.allied = False


class Strategy:
    def __init__(self, name, pref, action):
        self.name = name
        self.pref = pref
        self.action = action

    def apply(self, player, **context):
        out = self.action(player, **context)
        if isinstance(out, str):
            print(f'{player.first_name} {out}')


hide_strat = Strategy(
    'hide',
    lambda x, **c: (len(x.wounds) + 1) *
                   (x.current_area != START_AREA or x.health > x.max_health / 2) *
                   (x.max_health - x.health / 2) *
                   (1 - min(x.energy, x.sleep)) /
                   c[MAP].neighbors_count(x) + 0.1,
    lambda x, **c: x.hide(**c))
flee_strat = Strategy(
    'flee',
    lambda x, **c: (x.energy > x.move_cost) * (
        x.estimate_of_power(x.current_area, **c) / min(c[MAP].neighbors_count(x), 6) - x.dangerosity(**c)) + 0.1,
    lambda x, **c: x.flee(**c))
attack_strat = Strategy(
    'attack',
    lambda x, **c: x.health * min(x.energy, x.stomach, x.sleep) *
                   x.weapon.damage_mult / len(c[PLAYERS]),  # * (len(c[PLAYERS]) < 4),
    lambda x, **c: x.attack_at_random(**c))
ambush_strat = Strategy(
    'ambush',
    lambda x, **c: x.health * min(x.energy, x.stomach, x.sleep) *
                   x.weapon.damage_mult * (c[MAP].neighbors_count(x) == 1),
    lambda x, **c: x.set_up_ambush(**c))
hunt_player_strat = Strategy(
    'hunt player',
    lambda x, **c: x.health * x.weapon.damage_mult * (len(c[PLAYERS]) < 4),
    lambda x, **c: x.attack_at_random(**c))
fight_strat = Strategy(
    'fight',
    lambda x, **c: x.health * sum([x.dangerosity(**c) > n.dangerosity(**c) * 1.2 for n in c[MAP].neighbors(x)]),
    lambda x, **c: x.attack_at_random(**c))
duel_strat = Strategy(
    'duel',
    lambda x, **c: (len(c[PLAYERS]) == 2) * sum(
        [x.dangerosity(**c) > n.dangerosity(**c) * 1.2 for n in c[MAP].neighbors(x)]),
    lambda x, **c: x.attack_at_random(**c))
loot_strat = Strategy(
    'loot',
    lambda x, **c: (x.energy - x.move_cost) * (2 if x.weapon.damage_mult == 1 else 0.2) *
                   x.estimate(c[MAP].loot[x.current_area], **c),
    lambda x, **c: x.loot(**c))
loot_cornucopia_strat = Strategy(
    'loot cornucopia',
    lambda x, **c: (x.energy - x.move_cost) *
                   x.estimate(c[MAP].loot[START_AREA], **c) *
                   (x.current_area != START_AREA) *
                   (x.dangerosity(**c) - x.estimate_of_power(START_AREA, **c)),
    lambda x, **c: x.loot_cornucopia(**c))
loot_bag_strat = Strategy(
    'loot bag',
    lambda x, **c: x.weapon.damage_mult * c[MAP].has_bags(x) * (x.bag is None),
    lambda x, **c: x.loot_bag(**c))
loot_weapon_strat = Strategy(
    'loot weapon',
    lambda x, **c: x.estimate(c[MAP].weapons(x), **c),
    lambda x, **c: x.loot_weapon(**c))
forage_strat = Strategy(
    'forage',
    lambda x, **c: x.hunger * c[MAP].forage_potential(x) / c[MAP].neighbors_count(x),
    lambda x, **c: x.forage(**c))
dine_strat = Strategy(
    'dine',
    lambda x, **c: x.hunger * x.has_food / c[MAP].neighbors_count(x),
    lambda x, **c: x.dine(**c))
craft_strat_1 = Strategy(
    'craft',
    lambda x, **c: (x.energy - 0.2) * (2 - x.weapon.damage_mult) * (c[MAP].neighbors_count(x) < 2),
    lambda x, **c: x.craft(**c))
craft_strat_2 = Strategy(
    'craft',
    lambda x, **c: (x.energy - 0.2) * (x.weapon.damage_mult < 2) *
                   (2 - x.weapon.damage_mult) / c[MAP].neighbors_count(x),
    lambda x, **c: x.craft(**c))
trap_strat = Strategy(
    'build trap',
    lambda x, **c: (x.energy - 0.2) * (c[MAP].neighbors_count(x) < 2) * (can_build_any_trap(x, **c)),
    lambda x, **c: build_any_trap(x, **c))
free_trap_strat = Strategy(
    'free from trap',
    lambda x, **c: 1000 * (TRAPPED in x.status),
    lambda x, **c: x.free_from_trap(**c))

start_strategies = [
    flee_strat, fight_strat, loot_bag_strat, loot_weapon_strat,
]

morning_strategies = [
    hide_strat, flee_strat, attack_strat, loot_strat, craft_strat_1, forage_strat, dine_strat, loot_bag_strat,
    hunt_player_strat, ambush_strat, loot_cornucopia_strat, trap_strat, free_trap_strat, duel_strat,
]

night_strategies = [
    hide_strat, flee_strat, loot_strat, craft_strat_2, forage_strat, dine_strat, hunt_player_strat, ambush_strat,
    loot_cornucopia_strat, trap_strat, free_trap_strat,
]
