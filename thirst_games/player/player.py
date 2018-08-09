from typing import Dict, List, Optional, Union

from copy import copy
from random import random, choice

from thirst_games.abstract.entity import Entity, FightingEntity, LivingEntity
from thirst_games.abstract.items import Weapon, PoisonVial
from thirst_games.abstract.playing_entity import Strategy, PlayingEntity, Relationship, GroupedRelationship
from thirst_games.constants import (NIGHT, STARTER, TRAPPED, START_AREA, SLEEPING, FLEEING, AMBUSH, ARM_WOUND)
from thirst_games.context import Context
from thirst_games.map import Map, Area
from thirst_games.narrator import format_list, Narrator
from thirst_games.player.carrier import Carrier
from thirst_games.player.fight import do_a_fight
from thirst_games.traps import can_build_any_trap, build_any_trap
from thirst_games.weapons import weapon_bleed_proba


class Player(Carrier, PlayingEntity):

    def __init__(self, name: str, district: int, he) -> None:
        Carrier.__init__(self, name, he)
        self.wisdom = 0.9
        self._waiting = 0
        self.district = district
        self.relationships: Dict[str, Relationship] = {}

    def relationship(self, other_player) -> Relationship:
        if len(other_player.players) > 1:
            return GroupedRelationship([self.relationship(p) for p in other_player.players])
        if other_player.name not in self.relationships:
            self.relationships[other_player.name] = Relationship()
        return self.relationships[other_player.name]

    def is_allied_to(self, player):
        return self.relationship(player).allied

    def allies(self) -> List[PlayingEntity]:
        return [p for p in Context().alive_players if self.is_allied_to(p)]

    def present_allies(self) -> List[PlayingEntity]:
        return [p for p in Map().players(self) if self.is_allied_to(p) and p != self]

    def current_group(self) -> List[PlayingEntity]:
        return [*self.present_allies(), self]

    def busy_allies(self) -> List[PlayingEntity]:
        return [p for p in Context().alive_players if self.relationship(p).allied and p.busy]

    def enemies(self, area: Area) -> List[FightingEntity]:
        return [p for p in Context().playing_entities_at(area) if self not in p.players]

    def betray(self, player: PlayingEntity):
        self.relationship(player).set_allied(False)
        self.relationship(player).add_trust(-1)
        player.relationship(self).set_allied(False)
        player.relationship(self).add_trust(-1)
        player.relationship(self).add_friendship(-1)

        Narrator().new([self.name, 'betrays', player.name, '!'])
        Map().test = f'{self.name} betrays'

    def consider_betrayal(self):
        if len([p for p in Context().alive_players if p != self and not self.is_allied_to(p)]) == 0:
            allies = self.allies()
            if len(allies):
                allies.sort(key=lambda x: x.dangerosity)
                self.betray(allies[-1])  # betray the most dangerous one
                return True
        return False

    def want_to_ally(self, player: PlayingEntity) -> float:
        players = player.current_group()
        potential = sum([self._ally_potential(p) for p in players])
        return potential

    def _ally_potential(self, player: PlayingEntity) -> float:
        return player.dangerosity * max(self.relationship(player).friendship, self.relationship(player).trust)

    def think(self):
        if self.strategy is not None or self.acted:
            return
        strats = self.judge_strats()
        self.strategy = [s for s, v in strats.items() if v == max(strats.values())][0]
        # print(f'{self.name}:{self.strategy.name}')

    def judge_strats(self) -> dict:
        if self.sleep < 0:
            if Map().players_count(self) > 1 and self.energy > self.move_cost:
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
        return - len(self.enemies(area)) * 10 \
               + len(Map().loot(area)) \
               + (self.thirst if area.has_water else 0) \
               + (30 * len([a for a in self.allies() if a in area.players]) if area != self.current_area else 0) \
               + 1

    def _pursue_value(self, area):
        return -len(self.enemies(area)) * 10 \
               - (30 if area.is_start else 0) \
               + len(Map().loot(area)) \
               + (self.thirst if area.has_water else 0) \
               + 30 * len([a for a in self.allies() if a in area.players])

    def act(self):
        new_strat = self.new_strat()
        if new_strat is not None:
            self.apply_strat(new_strat)
        self.acted = True

    def new_strat(self) -> Optional[Strategy]:
        if self.acted or self.busy:
            return None
        if self.energy < 0:
            return Strategy('collapse', None, lambda x: x.go_to_sleep())
        elif Context().time == STARTER \
                and self.current_area.name == START_AREA \
                and len(self.enemies(self.current_area)) == 0:
            return Strategy('won bloodbath', None, lambda x: x.cornucopia_victory())
        return self.strategy

    def apply_strat(self, strategy: Optional[Strategy]):
        Narrator().cut()
        if self.acted or self.busy:
            return
        if strategy is None:
            strategy = self.strategy
        try:
            strategy.apply(self)
        except AttributeError as e:
            raise AttributeError(f'{self.name}({self.current_area.at}) has no strat ({self.strategy})') from e
        Narrator().cut()

    def should_go_get_drop(self, area: Area) -> float:
        area_value = self.dangerosity + self.estimate(Map().loot(area)) - self.estimate_of_danger(area)
        return area_value * min([random(), 3 / Context().player_count])

    def go_get_drop(self, area: Area):
        out = self.go_to(area)
        if out is not None:
            Narrator().add([self.name, f'goes {out.to} to get loot'])
        else:
            Narrator().cut()
        if self.check_for_ambush_and_traps():
            return
        seen_neighbors = [p for p in Map().potential_players(self) if self.can_see(p) and p != self]
        free_neighbors = [p for p in seen_neighbors if p.current_area == self.current_area and not p.busy]
        potential_danger = sum([p.dangerosity for p in seen_neighbors])
        actual_danger = sum([p.dangerosity for p in free_neighbors])

        if potential_danger > self.dangerosity and potential_danger > self.courage:
            Narrator().add([self.name, 'sees', format_list([p.name for p in seen_neighbors])])
            self.flee(filtered_areas=[area])
        elif actual_danger > self.dangerosity and actual_danger > self.courage:
            Narrator().add([self.name, 'sees', format_list([p.name for p in free_neighbors])])
            self.flee(filtered_areas=[area])
        elif actual_danger > 0:  # enemy present -> fight them
            Narrator().cut()
            self.attack_at_random()
        elif potential_danger > 0 and actual_danger == 0:  # enemy busy but incoming
            if self.dangerosity > potential_danger:  # attack before the other(s) arrive
                Narrator().cut()
                self.attack_at_random()
            else:  # loot and go/get your load and hit the road
                Narrator().add([self.name, 'avoids', format_list([p.name for p in seen_neighbors])])
                self.loot(take_a_break=False)
                self.flee(filtered_areas=[area])
        else:  # servez-vous
            self.loot()
        if len(Narrator().current_sentence) == 0:
            Narrator().add([
                self.name, f'potential_danger={potential_danger}', f'actual_danger={actual_danger}',
                f'dangerosity={self.dangerosity}', f'courage={self.courage}',
            ])

    def cornucopia_victory(self):
        self.loot_bag()
        self.loot_weapon()
        self.take_a_break()

    @property
    def courage(self) -> float:
        courage = (self.health / self.max_health) * self.energy + self._rage
        courage = courage + self.estimate(Map().loot(self)) * courage
        return courage

    @property
    def dangerosity(self) -> float:
        power = self.health * self._damage()
        if SLEEPING in self.status:
            power *= 0.1
        return power

    def flee(self, area=None, panic=False, drop_verb='drops', stock=False, filtered_areas=None):
        if area is None:
            if filtered_areas is None:
                filtered_areas = []
            filtered_areas = [*Context().forbidden_areas, *filtered_areas]
            self.status.append(FLEEING)
            if panic and random() > self.courage + 0.5:
                self.drop_weapon(verbose=True, drop_verb=drop_verb)

            available_areas = [area for area in Map().areas if area not in filtered_areas]
            available_areas.sort(key=lambda x: self._flee_value(x))
            area = available_areas[-1]

        out = self.go_to(area)
        if out is None:
            self.hide(panic=panic, stock=stock)
        else:
            Narrator().add([self.name, f'flees {out.to}'], stock=stock)
            self.check_for_ambush_and_traps()

    def pursue(self):
        available_areas = [a for a in Map().areas if a not in Context().forbidden_areas]
        available_areas.sort(key=lambda x: -self._pursue_value(x))
        out = self.go_to(available_areas[0])
        if out is None:
            self.hide()
            Narrator().replace('hides and rests', 'rests')
        else:
            targets = [p.name for p in Context().alive_players if p != self and not self.relationship(p).allied]
            if len(targets) == 0:
                Narrator().add([self.name, 'doesn\'t know', 'who to look for', out.at])
            else:
                players = 'players' if len(targets) > 1 else targets[0]
                Narrator().add([self.name, 'searches for', players, out.at])
            self.check_for_ambush_and_traps()

    def go_to(self, area: Union[str, Area, Entity]) -> Optional[Area]:
        area = Map().get_area(area)
        if area != self.current_area:
            self.reveal()
            self._energy -= self.move_cost
            self.busy = True
            return Map().move_player(self, area)
        return None

    def set_up_ambush(self):
        self.stealth += (random() / 2 + 0.5) * (1 - self.stealth)
        if AMBUSH not in self.status:
            self.status.append(AMBUSH)
            Map().add_ambusher(self, self)
            Narrator().add([self.name, 'sets up', 'an ambush', self.current_area.at])
        else:
            self._waiting += 1
            if self._waiting < 2:
                Narrator().add([self.name, 'keeps', 'hiding', self.current_area.at])
            else:
                Narrator().add([self.name, 'gets', 'tired of hiding', self.current_area.at])
                self.status.remove(AMBUSH)
                Map().remove_ambusher(self, self)
                self.pursue()

    def take_a_break(self):
        Carrier.take_a_break(self)
        self.poison_weapon()

    def estimate_of_power(self, area) -> float:
        neighbors = Map().players(area)
        if not len(neighbors):
            return 0
        seen_neighbors = [p for p in neighbors if self.can_see(p) and p != self]
        return sum([p.dangerosity for p in seen_neighbors])

    def estimate_of_danger(self, area) -> float:
        neighbors = Map().potential_players(area)
        if not len(neighbors):
            return 0
        seen_neighbors = [p for p in neighbors if self.can_see(p) and p != self]
        return sum([p.dangerosity for p in seen_neighbors])

    def can_see(self, other):
        if SLEEPING in self.status:
            return False
        stealth_mult = 1
        random_mult = (random() * 0.5 + 0.5)
        if other.current_area != self.current_area:
            stealth_mult *= 2
            random_mult = 1
        return random_mult * self.wisdom > other.stealth * stealth_mult

    def pillage(self, stuff):
        if len([p for p in Context().alive_players if p.is_alive]) == 1:
            return
        if Map().players_count(self) > 1:
            return
        looted = []
        for item in stuff:
            if item not in Map().loot(self.current_area):
                continue
            if isinstance(item, Weapon):
                if item.damage_mult > self.weapon.damage_mult:
                    looted.append(item)
                    Map().remove_loot(item, self.current_area)
            else:
                looted.append(item)
                Map().remove_loot(item, self.current_area)
        if not len(looted):
            return
        Narrator().add([self.name, 'loots', format_list([e.long_name for e in looted])])
        for item in looted:
            if isinstance(item, Weapon):
                self.get_weapon(item)
            else:
                self.get_item(item)

    def poison_weapon(self):
        if self.has_item(
                'poison vial') and weapon_bleed_proba.get(self.weapon.name, 0) > 0 and self.weapon.poison is None:
            vial = [p_v for p_v in self.equipment if isinstance(p_v, PoisonVial)][0]
            self.remove_item(vial)
            self.weapon.poison = vial.poison
            Narrator().add([self.name, 'puts', vial.poison.name, 'on', self.his, self.weapon.name])
            vial.poison.long_name = f'{self.name}\'s {vial.poison.name}'

    def attack_at_random(self):
        preys = [p for p in self.enemies(self.current_area) if self.can_see(p) and p != self]
        preys.sort(key=lambda x: x.dangerosity)
        if len(preys):
            self.fight(preys[0])
        else:
            self.pursue()

    def fight(self, other_player: FightingEntity):
        if isinstance(other_player, Player):
            self.relationship(other_player).allied = False
            other_player.relationship(self).allied = False
        do_a_fight(self.players, other_player.players)

    def hit(self, target: LivingEntity, mult=1) -> bool:
        if SLEEPING in target.status:
            target.status.remove(SLEEPING)
            mult *= 2
        if self.energy < 0.1:
            mult /= 2
            self._rage = -1
        else:
            self.add_energy(-0.1)
        hit_chance = mult if mult > 1 else 0.6 * mult
        if ARM_WOUND in self.status:
            hit_chance -= 0.2
        if TRAPPED in target.status:
            hit_chance += 0.3
        if random() < hit_chance:
            self._rage += 0.1
            if self.weapon.poison is not None and\
                            self.weapon.poison.long_name not in [p.long_name for p in target.active_poisons]:
                if random() > 0.3:
                    target.add_poison(copy(self.weapon.poison))
                self.weapon.poison.amount -= 1
                if self.weapon.poison.amount == 0:
                    self.weapon.poison = None
            return target.be_damaged(
                self.damage() * mult, weapon=self.weapon.name, attacker_name=self.name)
        else:  # Miss
            self._rage -= 0.1
            Narrator().stock([self.name, 'misses'])
            return False

    def _damage(self):
        mult = 1
        if ARM_WOUND in self.status:
            mult -= 0.2
        if TRAPPED in self.status:
            mult *= 0.5
        return mult * self.weapon.damage_mult / 2

    def damage(self):
        return self._damage() * random()

    def check_for_ambush_and_traps(self):
        traps = Map().traps(self)
        for t in traps:
            if t.check(self):
                t.apply(self)
                return True
        ambushers = Map().ambushers(self)
        if not len(ambushers):
            return False
        ambusher = choice(ambushers)
        ambusher.trigger_ambush(self)
        return True

    def trigger_ambush(self, prey):
        self.status.remove(AMBUSH)
        Map().remove_ambusher(self, self)
        Narrator().new([prey.name, 'falls', 'into', f'{self.name}\'s ambush!'])
        self.fight(prey)

    def loot_start(self):
        w = self.estimate(Map().weapons(self))
        b = self.weapon.damage_mult * Map().has_bags(self) * (self.bag is None)
        if w > b and w > 0:
            self.loot_weapon()
        elif b > 0:
            self.loot_bag(take_a_break=False)
        else:
            self.hide(panic=True)


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
        ) / Map().players_count(x), 0.1]),
    lambda x: x.hide())


class FleeStrat(Strategy):
    def __init__(self, area):
        Strategy.__init__(self, f'flee to {area.name}', None, None)
        self.area = area

        def _pref(x):
            return x._flee_value(self.area) / 30

        self.pref = _pref

    def apply(self, player: PlayingEntity):
        player.flee(self.area)


def flee_strats():
    return [FleeStrat(area) for area in Map().areas if area not in Context().forbidden_areas]


def get_drop_strats():
    return [Strategy(
        f'go get loot {area.at}',
        lambda x: x.should_go_get_drop(area),
        lambda x: x.go_get_drop(area)
    ) for area in Map().areas if area not in Context().forbidden_areas]


attack_strat = Strategy(
    'attack',
    lambda x: x.health * min(x.energy, x.stomach, x.sleep) *
                   x.weapon.damage_mult / Context().player_count,  # * (len(c[PLAYERS]) < 4),
    lambda x: x.attack_at_random())
ambush_strat = Strategy(
    'ambush',
    lambda x: x.health * min(x.energy, x.stomach, x.sleep) * x.weapon.damage_mult * (Map().players_count(x) == 1),
    lambda x: x.set_up_ambush())
hunt_player_strat = Strategy(
    'hunt player',
    lambda x: x.health * x.weapon.damage_mult * (Context().player_count < 4),
    lambda x: x.attack_at_random())
fight_strat = Strategy(
    'fight',
    lambda x: x.health * (sum([x.dangerosity > n.dangerosity * 1.2 for n in Map().players(x)]) + 0.1),
    lambda x: x.attack_at_random())
duel_strat = Strategy(
    'duel',
    lambda x: (Context().player_count == 2) * sum(
        [x.dangerosity > n.dangerosity * 1.2 for n in Map().players(x)]),
    lambda x: x.attack_at_random())
loot_strat = Strategy(
    'loot',
    lambda x: (x.energy - x.move_cost) * (2 if x.weapon.damage_mult == 1 else 0.2) * x.estimate(Map().loot(x)),
    lambda x: x.loot())
loot_bag_strat = Strategy(
    'loot bag',
    lambda x: x.weapon.damage_mult * Map().has_bags(x) * (x.bag is None),
    lambda x: x.loot_bag())
loot_start_strat = Strategy(
    'loot', lambda x: max(x.estimate(Map().weapons(x)), x.weapon.damage_mult * Map().has_bags(x) * (x.bag is None)),
    lambda x: x.loot_start())
forage_strat = Strategy(
    'forage',
    lambda x: x.hunger * Map().forage_potential(x) / Map().players_count(x),
    lambda x: x.forage())
dine_strat = Strategy(
    'dine',
    lambda x: x.hunger * x.has_food / Map().players_count(x),
    lambda x: x.dine())
craft_strat_1 = Strategy(
    'craft',
    lambda x: (2 - x.weapon.damage_mult) * (1 / Map().players_count(x)),
    lambda x: x.craft())
craft_strat_2 = Strategy(
    'craft',
    lambda x: (x.energy - 0.2) * (x.weapon.damage_mult < 2) * (2 - x.weapon.damage_mult) / Map().players_count(x),
    lambda x: x.craft())
trap_strat = Strategy(
    'build trap',
    lambda x: (x.energy - 0.2) * (Map().players_count(x) < 2) * (can_build_any_trap(x)),
    lambda x: build_any_trap(x))
free_trap_strat = Strategy(
    'free from trap',
    lambda x: 1000 * (TRAPPED in x.status),
    lambda x: x.free_from_trap())


def start_strategies():
    return [
        *flee_strats(), fight_strat, loot_start_strat,
    ]


def morning_strategies():
    return [
        hide_strat, *flee_strats(), attack_strat, loot_strat, craft_strat_1, forage_strat, dine_strat, loot_bag_strat,
        hunt_player_strat, ambush_strat, *get_drop_strats(), trap_strat, free_trap_strat, duel_strat,
    ]


def night_strategies():
    return [
        hide_strat, *flee_strats(), loot_strat, craft_strat_2, forage_strat, dine_strat, hunt_player_strat,
        ambush_strat, *get_drop_strats(), trap_strat, free_trap_strat,
    ]
