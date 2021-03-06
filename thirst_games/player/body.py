from random import random, choice
from typing import List

from thirst_games.abstract.entity import LivingEntity, Entity
from thirst_games.constants import (
    HEAD_WOUND, BELLY_WOUND, LEG_WOUND, BLEEDING, SLEEPING, THIRSTY, TRAPPED,
    NIGHT, AMBUSH, FLEEING, BURN_WOUND,
    START_AREA)
from thirst_games.context import Context
from thirst_games.map import Map
from thirst_games.narrator import Narrator, format_list
from thirst_games.poison import Poison
from thirst_games.weapons import get_weapon_wound, get_weapon_blood


class Body(LivingEntity):

    def __init__(self, name: str, he):
        LivingEntity.__init__(self, name, he)
        self._health = 1
        self._max_health = 1
        self._energy = 1
        self._sleep = 1
        self._stomach = 1
        self._water = 2
        self._rage = 0
        self._poisons: List[Poison] = []

    @property
    def is_alive(self):
        return self.health > 0

    @property
    def health(self):
        return max(0, self._health)

    @property
    def max_health(self):
        max_hp = self._max_health
        if BELLY_WOUND in self.status:
            max_hp = min(self.health, max_hp)
        return max_hp

    def add_health(self, amount):
        was_alive = self.is_alive
        self._health = min(self.max_health, self._health + amount)
        if self._health <= 0 and was_alive:
            self.die()

    @property
    def wounds(self):
        wounds = [w for w in self.status if w.find('wound') != -1]
        if BLEEDING in self.status:
            wounds.append(BLEEDING)
        return wounds

    @property
    def energy(self):
        return max(0, self._energy)

    def add_energy(self, amount):
        max_nrg = 1
        if HEAD_WOUND in self.status:
            max_nrg = 0.6
        self._energy = min(max_nrg, self._energy + amount)

        if self._energy < 0 and self.is_alive:
            if 'exhausted' not in self.status:
                # Narrator().add([self.name, 'needs', 'to rest'])
                self.status.append('exhausted')
            if self.stomach > 0:
                self.consume_nutriments(self._energy)
            elif self.sleep <= 0:
                self.add_health(self._energy)
                if not self.is_alive:
                    Narrator().add([self.name, 'dies', 'of hunger and exhaustion'])
                self._energy = 0
        else:
            if 'exhausted' in self.status:
                self.status.remove('exhausted')

    @property
    def sleep(self):
        return max(0, self._sleep)

    def add_sleep(self, amount):
        self._sleep = min(1, self._sleep + amount)
        if self._sleep < 0:
            if 'sleepy' not in self.status:
                # Narrator().add([self.name, 'needs', 'to sleep'])
                self.status.append('sleepy')
            self.add_energy(self._sleep)
            self._sleep = 0
        else:
            if 'sleepy' in self.status:
                self.status.remove('sleepy')

    @property
    def hunger(self):
        return 1 - self._stomach

    @property
    def stomach(self) -> float:
        return self._stomach

    def consume_nutriments(self, value):
        self._stomach += value
        if self._stomach < 0:
            if 'hungry' not in self.status:
                # Narrator().add([self.name, 'needs', 'to eat'])
                self.status.append('hungry')
            self.add_energy(self._stomach)
            self._stomach = 0
        else:
            if 'hungry' in self.status:
                self.status.remove('hungry')

    @property
    def thirst(self):
        return max(1 - self._water, 0)

    @property
    def water(self):
        return self._water

    def drink(self, amount):
        self._water += amount

    def water_upkeep(self):
        if self.water and 'thirsty' in self.status:
            self.status.remove('thirsty')

    @property
    def move_cost(self):
        cost = 0.3
        if LEG_WOUND in self.status:
            cost += 0.2
        return cost

    def can_flee(self):
        filtered_areas = Context().forbidden_areas
        accessible_areas = [a for a in Map().areas if a not in filtered_areas]
        if not len(accessible_areas):
            return False
        if TRAPPED in self.status:
            return False
        return self.energy + self.health > self.move_cost or not self.current_area.is_start

    def take_a_break(self):
        raise NotImplementedError

    def rest(self, stock=False):
        if self.current_area.name != START_AREA:
            self.stealth += random() * (1 - self.stealth)
            Narrator().add([self.name, 'hides', self.current_area.at], stock=stock)

        self.take_a_break()
        wounds = self.wounds
        if BLEEDING in wounds:
            self.patch(BLEEDING, stock=stock)
        elif len(wounds):
            self.patch(choice(wounds), stock=stock)
        else:
            self.add_health(max(self.energy, random()) * (self.max_health - self.health))
            self.add_energy(max(self.sleep, random()) * (1 - self.energy))
            Narrator().add([self.name, 'rests', self.current_area.at], stock=stock)

    def hide(self, panic=False, stock=False):
        if panic:
            Narrator().add([self.name, 'hides', self.current_area.at], stock=stock)
            return
        if self.sleep < 0.1 \
                or (Context().time == NIGHT and Map().players_count == 1 and len(self.wounds) == 0) \
                or (Map().players_count == 1 and self.sleep < 0.2 and len(self.wounds) == 0) \
                or (Context().time == NIGHT and self.sleep < 0.3 and len(self.wounds) == 0):
            self.go_to_sleep(stock=stock)
            return
        return self.rest(stock=stock)

    def reveal(self):
        Entity.reveal(self)
        self.end_ambush()

    def end_ambush(self):
        if AMBUSH in self.status:
            self.status.remove(AMBUSH)
            Map().remove_ambusher(self)

    def patch(self, wound: str, stock=False):
        raise NotImplementedError

    def go_to_sleep(self, stock=False):
        if self.energy < 0.2:
            Narrator().add([self.name, 'is exhausted'], stock=stock)
        self.add_health(self.energy * (1 - self.health))
        self.add_energy(self.sleep * (1 - self.energy))
        self.add_sleep(1)
        verb = 'sleeps' if self.energy > 0 else 'collapses'
        Narrator().add([self.name, verb, self.current_area.at], stock=stock)
        self.status.append(SLEEPING)

    def wake_up(self):
        if SLEEPING in self.status:
            self.status.remove(SLEEPING)

    def stop_running(self):
        if FLEEING in self.status:
            self.status.remove(FLEEING)

    @property
    def active_poisons(self) -> List[Poison]:
        return [p for p in self._poisons if p.amount > 0]

    def remove_poison(self, poison):
        poison.amount = 0
        Narrator().add([self.name, 'is', 'no longer affected by', poison.long_name])

    def add_poison(self, poison):
        self._poisons.append(poison)

    def free_from_trap(self):
        if TRAPPED in self.status:
            self.status.remove(TRAPPED)
            Narrator().new([self.name, 'frees', f'{self.him}self', 'from', 'the trap'])

    def upkeep(self):
        self.destination = None
        self.stop_running()

        dehydratation = 0.5 if BURN_WOUND in self.status else 0.3
        self._water -= dehydratation
        self.water_upkeep()
        energy_upkeep = -random() * 0.1  # loses energy while being awake
        sleep_upkeep = max(random(), random()) * 0.1
        food_upkeep = max(random(), random()) * 0.2
        if self.thirst > 1:
            self.status.append(THIRSTY)
            energy_upkeep *= self.thirst
        if SLEEPING in self.status:
            self.status.remove(SLEEPING)
            sleep_upkeep = 0
            energy_upkeep = 0
            food_upkeep /= 2
        energy_upkeep += min(sleep_upkeep, self.sleep)  # compensates with sleep reserves
        energy_upkeep += min(food_upkeep, self.stomach)  # compensates with food reserves
        self.add_sleep(-sleep_upkeep * 2)  # consumes sleep reserves
        self.consume_nutriments(-food_upkeep)  # consumes food reserves
        self.add_energy(energy_upkeep + sleep_upkeep + food_upkeep)

        if BLEEDING in self.status:
            if self.be_damaged(max(0.05, self.health / 5)):
                Narrator().add([self.name, 'bleeds', 'to death'])
        for poison in self.active_poisons:
            poison.upkeep(self)
        self._rage = 0

    def be_damaged(self, damage, weapon='default', attacker_name=None) -> bool:
        self._rage += random() / 4 - damage
        if not self.is_alive:
            print(f'{self.name} is already dead')
            return False
        self.add_health(-damage)
        if self.is_alive and damage > 0.3:
            wound_element = get_weapon_wound(weapon)
            bleeding = get_weapon_blood(weapon)
            wound = wound_element + ' wound' if wound_element is not None else None
            if wound is not None and bleeding:
                self.status.append(wound)
                self.status.append(BLEEDING)
                if attacker_name is None:
                    Narrator().stock([
                        self.name, 'suffers', 'a bleeding', wound])
                else:
                    Narrator().stock([attacker_name, 'wounds', self.him, 'deeply', 'at the', wound_element])
            elif wound is not None:
                self.status.append(wound)
                if attacker_name is None:
                    Narrator().stock([
                        self.name, 'suffers', 'an' if wound[0] in ['a', 'e', 'i', 'o', 'u', 'y'] else 'a', wound])
                else:
                    Narrator().stock([attacker_name, 'wounds', self.him, 'at the', wound_element])
            elif bleeding:
                self.status.append(BLEEDING)
                if attacker_name is None:
                    Narrator().stock([
                        self.name, 'suffers', 'a bleeding wound'])
                else:
                    Narrator().stock([attacker_name, 'wounds', self.him, 'deeply'])
            if wound is not None:
                self._max_health *= 0.9

        return not self.is_alive

    def die(self):
        Context().death(self)

    @property
    def drops(self):
        return []

    @property
    def full_status_desc(self):
        return format_list([*self.status, *[str(p) for p in self._poisons]])
