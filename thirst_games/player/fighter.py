from copy import copy
from random import random

from thirst_games.constants import (
    MAP, SLEEPING, FLEEING, PANIC, NARRATOR, PLAYERS, AMBUSH, TRAPPED, TIME, STARTER,
    ARM_WOUND
)
from thirst_games.items import Weapon, PoisonVial
from thirst_games.map import START_AREA
from thirst_games.narrator import format_list
from thirst_games.player.body import Body
from thirst_games.player.carrier import Carrier
from thirst_games.weapons import weapon_bleed_proba


class Fighter(Carrier):
    def __init__(self, first_name: str, his='their'):
        Carrier.__init__(self, first_name, his)
        self.busy = False
        self.wisdom = 0.9
        self._waiting = 0

    def courage(self, **context):
        courage = self.health * self.energy + self._rage
        if MAP in context:
            courage = max([courage, self.estimate(context[MAP].loot[self.current_area], **context)])
        return courage

    def dangerosity(self, **context):
        power = self.health * self._damage(**context)
        if SLEEPING in self.status:
            power *= 0.1
        return power

    def flee(self, panic=False, **context):
        self.status.append(FLEEING)
        if panic and random() > self.courage(**context) + 0.5:
            self.drop_weapon(True, **context)
        min_player_per_area = min([len(area) for key, area in context[MAP].areas.items() if key != START_AREA])
        # can't flee to or hide at the cornucopia
        best_areas = [
            key for key, value in context[MAP].areas.items() if len(value) == min_player_per_area and key != START_AREA
        ]
        best_areas.sort(key=lambda x: -len(context[MAP].loot[x]))
        best_area = best_areas[0]
        if 'thirsty' in self.status and 'the river' in best_areas:
            best_area = 'the river'
        out = self.go_to(best_area, **context, **{PANIC: True})
        if out is not None:
            context[NARRATOR].add([self.first_name, f'flees to {out}'])
            self.check_for_ambush_and_traps(**context)

    def pursue(self, **context):
        max_player_per_area = max([len(area) for area in context[MAP].areas.values()])
        best_areas = [key for key, value in context[MAP].areas.items() if len(value) == max_player_per_area]
        best_areas.sort(key=lambda x: -len(context[MAP].loot[x]))
        best_area = best_areas[0]
        if 'thirsty' in self.status and 'the river' in best_areas:
            best_area = 'the river'
        out = self.go_to(best_area, **context)
        if out is None:
            context[NARRATOR].replace('hides and rests', 'rests')
        else:
            targets = [p.first_name for p in context[PLAYERS] if p != self]
            players = 'players' if len(targets) > 1 else targets[0]
            context[NARRATOR].add([self.first_name, 'searches for', players, f'at {out}'])
            self.check_for_ambush_and_traps(**context)

    def go_to(self, area, **context):
        if area != self.current_area and self.energy >= self.move_cost:
            self.reveal()
            self._energy -= self.move_cost
            self.busy = True
            return context[MAP].move_player(self, area)
        else:
            self._energy -= self.move_cost
            self.hide(**context)

    def set_up_ambush(self, **context):
        self.stealth += (random() / 2 + 0.5) * (1 - self.stealth)
        if AMBUSH not in self.status:
            self.status.append(AMBUSH)
            context[NARRATOR].add([self.first_name, 'sets up', 'an ambush', f'at {self.current_area}'])
        else:
            self._waiting += 1
            if self._waiting < 2:
                context[NARRATOR].add([self.first_name, 'keeps', 'hiding', f'at {self.current_area}'])
            else:
                context[NARRATOR].add([self.first_name, 'gets', 'tired of hiding', f'at {self.current_area}'])
                self.status.remove(AMBUSH)
                self.pursue(**context)

    def take_a_break(self, **context):
        Carrier.take_a_break(self, **context)
        self.poison_weapon(**context)

    def estimate_of_power(self, area, **context) -> float:
        neighbors = context[MAP].neighbors(self, area)
        if not len(neighbors):
            return 0
        seen_neighbors = [p for p in neighbors if self.can_see(p)]
        return sum([p.dangerosity(**context) for p in seen_neighbors])

    def can_see(self, other: Carrier):
        stealth_mult = 1
        if other.current_area != self.current_area:
            stealth_mult *= 1.5
        return (random() * 0.5 + 0.5) * self.wisdom > other.stealth * stealth_mult

    def pillage(self, stuff, **context):
        if len([p for p in context[PLAYERS] if p.is_alive]) == 1:
            return
        if context[MAP].neighbors_count(self) > 1:
            return
        looted = []
        for item in stuff:
            if item not in context[MAP].loot[self.current_area]:
                continue
            if isinstance(item, Weapon):
                if item.damage_mult > self.weapon.damage_mult:
                    looted.append(item)
                    context[MAP].remove_loot(item, self.current_area)
            else:
                looted.append(item)
                context[MAP].remove_loot(item, self.current_area)
        if not len(looted):
            return
        context[NARRATOR].add([self.first_name, 'loots', format_list([e.long_name for e in looted])])
        for item in looted:
            if isinstance(item, Weapon):
                self.get_weapon(item, **context)
            else:
                self.get_item(item, **context)

    def poison_weapon(self, **context):
        if self.has_item(
                'poison vial') and weapon_bleed_proba.get(self.weapon.name, 0) > 0 and self.weapon.poison is None:
            vial = [p_v for p_v in self.equipment if isinstance(p_v, PoisonVial)][0]
            self.remove_item(vial)
            self.weapon.poison = vial.poison
            context[NARRATOR].add([self.first_name, 'puts', vial.poison.name, 'on', self.his, self.weapon.name])
            vial.poison.long_name = f'{self.first_name}\'s {vial.poison.name}'

    def attack_at_random(self, **context):
        preys = [p for p in context[MAP].areas[self.current_area] if random() * self.wisdom > p.stealth and p != self]
        preys.sort(key=lambda x: x.health * x.damage(**context))
        if len(preys):
            self.fight(preys[0], **context)
        else:
            self.pursue(**context)

    def fight(self, other_player: Carrier, **context):
        self.busy = True
        other_player.busy = True

        verb = 'catches and attacks' if FLEEING in other_player.status else 'attacks'
        if FLEEING in other_player.status:
            other_player.status.remove(FLEEING)
        weapon = f'with {self.his} {self.weapon.name}'
        self_stuff = []
        other_weapon = f'with {other_player.his} {other_player.weapon.name}'
        other_stuff = []
        area = f'at {self.current_area}'
        surprise_mult = 2 if SLEEPING in other_player.status else (
            2 if TRAPPED in other_player.status else (
                1.5 if random() + self.stealth > other_player.wisdom else 1
            ))
        surprise = f'in {other_player.his} sleep' if SLEEPING in other_player.status else (
            f'while {other_player.he} is trapped' if TRAPPED in other_player.status else (
                'by surprise' if surprise_mult > 1 else ''))
        self.reveal()
        other_player.reveal()
        round = 1

        if self.hit(other_player, surprise_mult, **context):
            context[NARRATOR].add([
                self.first_name, 'kills', other_player.first_name, surprise, area, weapon])
            other_stuff = other_player.drops
        else:
            while True:
                context[NARRATOR].new([self.first_name, verb, other_player.first_name, area, weapon])
                context[NARRATOR].apply_stock()
                verb = 'fights'
                area = ''
                if random() > other_player.courage(**context) and other_player.can_flee(**context):
                    other_stuff = [other_player.weapon]
                    other_player.flee(True, **context)
                    other_stuff = other_stuff if not other_player.has_weapon else []
                    break
                if other_player.hit(self, **context):
                    context[NARRATOR].add(['and'])
                    context[NARRATOR].add([other_player.first_name, 'kills', self.him, 'in self-defense', other_weapon])
                    self_stuff = self.drops
                    break
                context[NARRATOR].add([other_player.first_name, 'fights back', other_weapon])
                context[NARRATOR].apply_stock()
                if random() > self.courage(**context) and self.can_flee(**context):
                    self_stuff = [self.weapon]
                    self.flee(True, **context)
                    self_stuff = self_stuff if not self.has_weapon else []
                    break
                if context[TIME] == STARTER and round > 3:
                    break
                round += 1
                if self.hit(other_player, **context):
                    context[NARRATOR].new([self.first_name, verb, 'and', 'kills', other_player.first_name, weapon])
                    other_stuff = other_player.drops
                    break
        self.pillage(other_stuff, **context)
        other_player.pillage(self_stuff, **context)

    def hit(self, target: Body, mult=1, **context) -> bool:
        if self.energy < 0.1:
            mult /= 2
            self._rage = -1
        else:
            self.add_energy(-0.1, **context)
        hit_chance = mult if mult > 1 else 0.6 * mult
        if ARM_WOUND in self.status:
            hit_chance -= 0.2
        if random() < hit_chance:
            self._rage += 0.1
            if self.weapon.poison is not None and\
                            self.weapon.poison.long_name not in [p.long_name for p in target.active_poisons]:
                if random() > 0.3:
                    target.add_poison(copy(self.weapon.poison), **context)
                self.weapon.poison.amount -= 1
                if self.weapon.poison.amount == 0:
                    self.weapon.poison = None
            return target.be_damaged(
                self.damage(**context) * mult, weapon=self.weapon.name, attacker_name=self.first_name, **context)
        else:  # Miss
            self._rage -= 0.1
            context[NARRATOR].stock([self.first_name, 'misses'])
            return False

    def _damage(self, **context):
        mult = 1
        if ARM_WOUND in self.status:
            mult -= 0.2
        if TRAPPED in self.status:
            mult *= 0.5
        return mult * self.weapon.damage_mult / 2

    def damage(self, **context):
        return self._damage(**context) * random()
