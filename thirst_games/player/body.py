from random import random, choice
from typing import List

from thirst_games.constants import NARRATOR, HEAD_WOUND, BELLY_WOUND, LEG_WOUND, BLEEDING, SLEEPING, THIRSTY, TRAPPED, \
    MAP, PANIC, TIME, NIGHT, AMBUSH, DEATH, FLEEING, BURN_WOUND
from thirst_games.map import Positionable, START_AREA
from thirst_games.poison import Poison
from thirst_games.weapons import get_weapon_wound, get_weapon_blood


class Body(Positionable):
    def __init__(self, first_name: str, his='their'):
        self.first_name = first_name
        self.his = his
        self.him = 'him' if his == 'his' else ('her' if his == 'her' else 'them')
        self.he = 'he' if his == 'his' else ('her' if his == 'her' else 'them')
        self._health = 1
        self._max_health = 1
        self._energy = 1
        self._sleep = 1
        self._stomach = 1
        self._water = 2
        self._rage = 0
        self._poisons: List[Poison] = []
        self.stealth = 0
        self.status = []

    @property
    def name(self):
        return self.first_name

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

    def add_health(self, amount, **context):
        was_alive = self.is_alive
        self._health = min(self.max_health, self._health + amount)
        if self._health <= 0 and was_alive:
            self.die(**context)

    @property
    def wounds(self):
        wounds = [w for w in self.status if w.find('wound') != -1]
        if BLEEDING in self.status:
            wounds.append(BLEEDING)
        return wounds

    @property
    def energy(self):
        return max(0, self._energy)

    def add_energy(self, amount, **context):
        max_nrg = 1
        if HEAD_WOUND in self.status:
            max_nrg = 0.6
        self._energy = min(max_nrg, self._energy + amount)

        if self._energy < 0:
            if 'exhausted' not in self.status:
                # context[NARRATOR].add([self.first_name, 'needs', 'to rest'])
                self.status.append('exhausted')
            self.add_health(self._energy, **context)
            if not self.is_alive:
                context[NARRATOR].add([self.first_name, 'dies of exhaustion'])
            self._energy = 0
        else:
            if 'exhausted' in self.status:
                self.status.remove('exhausted')

    @property
    def sleep(self):
        return max(0, self._sleep)

    def add_sleep(self, amount, **context):
        self._sleep = min(1, self._sleep + amount)
        if self._sleep < 0:
            if 'sleepy' not in self.status:
                # context[NARRATOR].add([self.first_name, 'needs', 'to sleep'])
                self.status.append('sleepy')
            self.add_energy(self._sleep, **context)
            self._sleep = 0
        else:
            if 'sleepy' in self.status:
                self.status.remove('sleepy')

    @property
    def hunger(self):
        return 1 - self._stomach

    @property
    def stomach(self):
        return self._stomach

    def consume_nutriments(self, value, **context):
        self._stomach += value
        if self._stomach < 0:
            if 'hungry' not in self.status:
                # context[NARRATOR].add([self.first_name, 'needs', 'to eat'])
                self.status.append('hungry')
            self.add_energy(self._stomach, **context)
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

    def can_flee(self, **context):
        if TRAPPED in self.status:
            return False
        return self.energy + self.health > self.move_cost or self.current_area != START_AREA

    def take_a_break(self, **context):
        raise NotImplementedError

    def rest(self, **context):
        if self.current_area != START_AREA:
            self.stealth += random() * (1 - self.stealth)
            context[NARRATOR].add([self.first_name, 'hides', f'at {self.current_area}'])

        self.take_a_break(**context)
        wounds = self.wounds
        if BLEEDING in wounds:
            self.patch(BLEEDING, **context)
        elif len(wounds):
            self.patch(choice(wounds), **context)
        else:
            self.add_health(max(self.energy, random()) * (self.max_health - self.health))
            self.add_energy(max(self.sleep, random()) * (1 - self.energy))
            context[NARRATOR].add([self.first_name, 'rests', f'at {self.current_area}'])

    def hide(self, **context):
        if context.get(PANIC, False):
            context[NARRATOR].add([self.first_name, 'hides', f'at {self.current_area}'])
            return
        if self.sleep < 0.1 \
                or (context[TIME] == NIGHT and context[MAP].neighbors_count == 1 and len(self.wounds) == 0) \
                or (context[MAP].neighbors_count == 1 and self.sleep < 0.2 and len(self.wounds) == 0) \
                or (context[TIME] == NIGHT and self.sleep < 0.3 and len(self.wounds) == 0):
            self.go_to_sleep(**context)
            return
        return self.rest(**context)

    def reveal(self):
        self.stealth = 0
        if AMBUSH in self.status:
            self.status.remove(AMBUSH)

    def patch(self, wound: str, **context):
        raise NotImplementedError

    def go_to_sleep(self, **context):
        if self.energy < 0.2:
            context[NARRATOR].add([self.first_name, 'is exhausted'])
        self.add_health(self.energy * (1 - self.health), **context)
        self.add_energy(self.sleep * (1 - self.energy), **context)
        self.add_sleep(1, **context)
        context[NARRATOR].add([self.first_name, 'sleeps', f'at {self.current_area}'])
        self.status.append(SLEEPING)

    def stop_running(self):
        if FLEEING in self.status:
            self.status.remove(FLEEING)

    @property
    def active_poisons(self) -> List[Poison]:
        return [p for p in self._poisons if p.amount > 0]

    def remove_poison(self, poison, **context):
        poison.amount = 0
        context[NARRATOR].add([self.first_name, 'is', 'no longer affected by', poison.long_name])

    def add_poison(self, poison, **context):
        self._poisons.append(poison)

    def check_for_ambush_and_traps(self, **context):
        traps = context[MAP].traps[self.current_area]
        for t in traps:
            if t.check(self, **context):
                t.apply(self, **context)
                return True
        ambushers = [p for p in context[MAP].neighbors(self) if AMBUSH in p.status and SLEEPING not in p.status]
        if not len(ambushers):
            return False
        ambusher = choice(ambushers)
        ambusher.status.remove(AMBUSH)
        context[NARRATOR].new([self.first_name, 'falls', 'into', f'{ambusher.first_name}\'s ambush!'])
        ambusher.fight(self, **context)
        return True

    def free_from_trap(self, **context):
        if TRAPPED in self.status:
            self.status.remove(TRAPPED)
            context[NARRATOR].new([self.first_name, 'frees', f'{self.him}self', 'from', 'the trap'])

    def upkeep(self, **context):
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
        self.add_sleep(-sleep_upkeep * 2, **context)  # consumes sleep reserves
        self.consume_nutriments(-food_upkeep, **context)  # consumes food reserves
        self.add_energy(energy_upkeep + sleep_upkeep + food_upkeep, **context)

        if BLEEDING in self.status:
            if self.be_damaged(max(0.05, self.health / 5), **context):
                context[NARRATOR].add([self.first_name, 'bleeds', 'to death'])
        for poison in self.active_poisons:
            poison.upkeep(self, **context)
        self._rage = 0

    def be_damaged(self, damage, weapon='default', attacker_name=None, **context) -> bool:
        self._rage += random() / 4 - damage
        if not self.is_alive:
            print(f'{self.first_name} is already dead')
            return False
        self.add_health(-damage, **context)
        if self.is_alive and damage > 0.3:
            wound_element = get_weapon_wound(weapon)
            bleeding = get_weapon_blood(weapon)
            wound = wound_element + ' wound' if wound_element is not None else None
            if wound is not None and bleeding:
                self.status.append(wound)
                self.status.append(BLEEDING)
                if attacker_name is None:
                    context[NARRATOR].stock([
                        self.first_name, 'suffers', 'a bleeding', wound])
                else:
                    context[NARRATOR].stock([attacker_name, 'wounds', self.him, 'deeply', 'at the', wound_element])
            elif wound is not None:
                self.status.append(wound)
                if attacker_name is None:
                    context[NARRATOR].stock([
                        self.first_name, 'suffers', 'an' if wound[0] in ['a', 'e', 'i', 'o', 'u', 'y'] else 'a', wound])
                else:
                    context[NARRATOR].stock([attacker_name, 'wounds', self.him, 'at the', wound_element])
            elif bleeding:
                self.status.append(BLEEDING)
                if attacker_name is None:
                    context[NARRATOR].stock([
                        self.first_name, 'suffers', 'a bleeding wound'])
                else:
                    context[NARRATOR].stock([attacker_name, 'wounds', self.him, 'deeply'])
            if wound is not None:
                self._max_health *= 0.9

        return not self.is_alive

    def die(self, **context):
        # self.drop_weapon(False, **context)
        # for e in self._equipment:
        #     context[MAP].add_loot(e, self.current_area)
        context[DEATH](self, **context)
