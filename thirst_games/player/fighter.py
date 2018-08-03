from typing import Union, Optional

from copy import copy
from random import random

from thirst_games.constants import (
    SLEEPING, FLEEING, AMBUSH, TRAPPED, STARTER, ARM_WOUND, THIRSTY)
from thirst_games.context import Context
from thirst_games.items import Weapon, PoisonVial
from thirst_games.map import Area, Positionable
from thirst_games.narrator import format_list, Narrator
from thirst_games.player.body import Body
from thirst_games.player.carrier import Carrier
from thirst_games.weapons import weapon_bleed_proba


class Fighter(Carrier):
    def __init__(self, first_name: str, his='their'):
        Carrier.__init__(self, first_name, his)
        self.busy = False
        self.wisdom = 0.9
        self._waiting = 0

    def courage(self):
        courage = (self.health / self.max_health) * self.energy + self._rage
        courage = courage + self.estimate(self.map.loot(self)) * courage
        return courage

    def dangerosity(self):
        power = self.health * self._damage()
        if SLEEPING in self.status:
            power *= 0.1
        return power

    def flee(self, panic=False, drop_verb='drops', stock=False):
        filtered_areas = Context().forbidden_areas
        self.status.append(FLEEING)
        if panic and random() > self.courage() + 0.5:
            self.drop_weapon(verbose=True, drop_verb=drop_verb)

        available_areas = [area for area in self.map.areas if area not in filtered_areas]
        available_areas.sort(
            key=lambda x: len(x.players) * 10 + (30 if x.is_start else 0)
                          - len(self.map.loot(x)) - (self.thirst if x.has_water else 0))

        out = self.go_to(available_areas[0])
        if out is None:
            self.hide(panic=panic, stock=stock)
        else:
            Narrator().add([self.first_name, f'flees {out.to}'], stock=stock)
            self.check_for_ambush_and_traps()

    def pursue(self):
        available_area = [a for a in self.map.areas if a not in Context().forbidden_areas]
        max_player_per_area = max([len(area.players) for area in available_area])
        best_areas = [area for area in available_area if len(area.players) == max_player_per_area]
        if THIRSTY in self.status and len([a for a in best_areas if a.has_water]):
            best_areas = [a for a in best_areas if a.has_water]
        best_areas.sort(key=lambda x: -len(self.map.loot(x)))
        best_area = best_areas[0]
        out = self.go_to(best_area)
        if out is None:
            self.hide()
            Narrator().replace('hides and rests', 'rests')
        else:
            targets = [p.first_name for p in Context().alive_players if p != self]
            players = 'players' if len(targets) > 1 else targets[0]
            Narrator().add([self.first_name, 'searches for', players, out.at])
            self.check_for_ambush_and_traps()

    def go_to(self, area: Union[str, Area, Positionable]) -> Optional[Area]:
        area = self.map.get_area(area)
        if area != self.current_area:
            self.reveal()
            self._energy -= self.move_cost
            self.busy = True
            return self.map.move_player(self, area)
        return None

    def set_up_ambush(self):
        self.stealth += (random() / 2 + 0.5) * (1 - self.stealth)
        if AMBUSH not in self.status:
            self.status.append(AMBUSH)
            Narrator().add([self.first_name, 'sets up', 'an ambush', self.current_area.at])
        else:
            self._waiting += 1
            if self._waiting < 2:
                Narrator().add([self.first_name, 'keeps', 'hiding', self.current_area.at])
            else:
                Narrator().add([self.first_name, 'gets', 'tired of hiding', self.current_area.at])
                self.status.remove(AMBUSH)
                self.pursue()

    def take_a_break(self):
        Carrier.take_a_break(self)
        self.poison_weapon()

    def estimate_of_power(self, area) -> float:
        neighbors = self.map.players(area)
        if not len(neighbors):
            return 0
        seen_neighbors = [p for p in neighbors if self.can_see(p) and p != self]
        return sum([p.dangerosity() for p in seen_neighbors])

    def estimate_of_danger(self, area) -> float:
        neighbors = self.map.potential_players(area)
        if not len(neighbors):
            return 0
        seen_neighbors = [p for p in neighbors if self.can_see(p) and p != self]
        return sum([p.dangerosity() for p in seen_neighbors])

    def can_see(self, other: Carrier):
        stealth_mult = 1
        random_mult = (random() * 0.5 + 0.5)
        if other.current_area != self.current_area:
            stealth_mult *= 2
            random_mult = 1
        return random_mult * self.wisdom > other.stealth * stealth_mult

    def pillage(self, stuff):
        if len([p for p in Context().alive_players if p.is_alive]) == 1:
            return
        if self.map.players_count(self) > 1:
            return
        looted = []
        for item in stuff:
            if item not in self.map.loot(self.current_area):
                continue
            if isinstance(item, Weapon):
                if item.damage_mult > self.weapon.damage_mult:
                    looted.append(item)
                    self.map.remove_loot(item, self.current_area)
            else:
                looted.append(item)
                self.map.remove_loot(item, self.current_area)
        if not len(looted):
            return
        Narrator().add([self.first_name, 'loots', format_list([e.long_name for e in looted])])
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
            Narrator().add([self.first_name, 'puts', vial.poison.name, 'on', self.his, self.weapon.name])
            vial.poison.long_name = f'{self.first_name}\'s {vial.poison.name}'

    def attack_at_random(self):
        preys = [p for p in self.map.players(self) if self.can_see(p) and p != self]
        preys.sort(key=lambda x: x.health * x.damage())
        if len(preys):
            self.fight(preys[0])
        else:
            self.pursue()

    def fight(self, other_player: Carrier):
        self.busy = True
        other_player.busy = True

        verb = 'catches and attacks' if FLEEING in other_player.status else (
            'finds and attacks' if other_player.stealth else 'attacks')
        if FLEEING in other_player.status:
            other_player.status.remove(FLEEING)
        weapon = f'with {self.his} {self.weapon.name}'
        self_stuff = []
        other_weapon = f'with {other_player.his} {other_player.weapon.name}'
        other_stuff = []
        area = self.current_area.at
        surprise_mult = 2 if SLEEPING in other_player.status else (
            2 if TRAPPED in other_player.status else (
                1.5 if not other_player.can_see(self) else 1
            ))
        surprise = f'in {other_player.his} sleep' if SLEEPING in other_player.status else (
            f'while {other_player.he} is trapped' if TRAPPED in other_player.status else (
                'by surprise' if surprise_mult > 1 else ''))
        self.reveal()
        other_player.reveal()
        round = 1

        if self.hit(other_player, surprise_mult):
            Narrator().add([
                self.first_name, 'kills', other_player.first_name, surprise, area, weapon])
            other_stuff = other_player.drops
        else:
            while True:
                Narrator().new([self.first_name, verb, other_player.first_name, area, weapon])
                Narrator().apply_stock()
                verb = 'fights'
                area = ''
                if random() > other_player.courage() and other_player.can_flee():
                    other_stuff = [other_player.weapon]
                    other_player.flee(panic=True)
                    other_stuff = other_stuff if not other_player.has_weapon else []
                    break
                if other_player.hit(self):
                    Narrator().add(['and'])
                    Narrator().add([other_player.first_name, 'kills', self.him, 'in self-defense', other_weapon])
                    self_stuff = self.drops
                    break
                Narrator().add([other_player.first_name, 'fights back', other_weapon])
                Narrator().apply_stock()
                if random() > self.courage() and self.can_flee():
                    self_stuff = [self.weapon]
                    self.flee(panic=True)
                    self_stuff = self_stuff if not self.has_weapon else []
                    break
                if Context().time == STARTER and round > 3:
                    break
                round += 1
                if self.hit(other_player):
                    Narrator().new([self.first_name, verb, 'and', 'kills', other_player.first_name, weapon])
                    other_stuff = other_player.drops
                    break
        self.pillage(other_stuff)
        other_player.pillage(self_stuff)

    def hit(self, target: Body, mult=1) -> bool:
        if SLEEPING in target.status:
            target.status.remove(SLEEPING)
        if self.energy < 0.1:
            mult /= 2
            self._rage = -1
        else:
            self.add_energy(-0.1)
        hit_chance = mult if mult > 1 else 0.6 * mult
        if ARM_WOUND in self.status:
            hit_chance -= 0.2
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
                self.damage() * mult, weapon=self.weapon.name, attacker_name=self.first_name)
        else:  # Miss
            self._rage -= 0.1
            Narrator().stock([self.first_name, 'misses'])
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
