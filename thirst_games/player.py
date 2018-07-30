from copy import copy
from random import random, choice
from typing import Dict, List, Union, Optional

from thirst_games.constants import MAP, PLAYERS, DEATH, TIME, NARRATOR, PANIC, SLEEPING, NIGHT, STARTER
from thirst_games.items import HANDS, Weapon, Item, Food, Bag, Bottle
from thirst_games.map import START_AREA, Positionable
from thirst_games.narrator import format_list
from thirst_games.traps import can_build_any_trap, build_any_trap
from thirst_games.weapons import get_weapon_wound, get_weapon_blood

FLEEING = 'fleeing'
AMBUSH = 'ambush'

ARM_WOUND = 'arm wound'
LEG_WOUND = 'leg wound'
BELLY_WOUND = 'belly wound'
HEAD_WOUND = 'head wound'
BLEEDING = 'bleeding'


class Player(Positionable):
    def __init__(self, first_name: str, district: int, his='their'):
        self.first_name = first_name
        self.district = district
        self.his = his
        self.him = 'him' if his == 'his' else ('her' if his == 'her' else 'them')
        self.relationships: Dict[Player, Relationship] = {}
        self.busy = False
        self._health = 1
        self._max_health = 1
        self._energy = 1
        self._sleep = 1
        self._stomach = 1
        self._water = 2
        self.stealth = 0
        self.wisdom = 0.9
        self._equipment: List[Item] = []
        self.status = []
        self._rage = 0
        self._waiting = 0

        self.strategy = None
        self.weapon = HANDS

    @property
    def name(self):
        return self.first_name

    @property
    def bag(self):
        bags = [e for e in self._equipment if isinstance(e, Bag)]
        if not len(bags):
            return None
        return bags[0]

    @property
    def equipment(self):
        bags = [e for e in self._equipment if isinstance(e, Bag)]
        return [*[e for e in self._equipment if not isinstance(e, Bag)], *[e for b in bags for e in b.content]]

    def has_item(self, item_name):
        return item_name in [i.name for i in self.equipment]

    @property
    def drops(self):
        stuff = copy(self._equipment)
        if self.weapon != HANDS:
            stuff.append(self.weapon)
        return stuff

    @property
    def is_alive(self):
        return self.health > 0

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
                context[NARRATOR].add([self.first_name, 'needs', 'to rest'])
                self.status.append('exhausted')
            self.add_health(self._energy, **context)
            if not self.is_alive:
                context[NARRATOR].add([self.first_name, 'dies of exhaustion'])
            self._energy = 0
        else:
            if 'exhausted' in self.status:
                self.status.remove('exhausted')

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
    def sleep(self):
        return max(0, self._sleep)

    @property
    def hunger(self):
        return 1 - self._stomach

    @property
    def stomach(self):
        return self._stomach

    @property
    def thirst(self):
        return max(1 - self._water, 0)

    @property
    def water(self):
        return self._water

    @property
    def move_cost(self):
        cost = 0.3
        if LEG_WOUND in self.status:
            cost += 0.2
        return cost

    @property
    def wounds(self):
        wounds = [w for w in self.status if w.find('wound') != -1]
        if BLEEDING in self.status:
            wounds.append(BLEEDING)
        return wounds

    def courage(self, **context):
        courage = self.health * self.energy + self._rage
        if MAP in context:
            courage = max([courage, self.estimate(context[MAP].loot[self.current_area], **context)])
        return courage

    def dangerosity(self, **context):
        power = self.health * self.damage(**context)
        if SLEEPING in self.status:
            power *= 0.1
        return power

    def add_sleep(self, amount, **context):
        self._sleep = min(1, self._sleep + amount)
        if self._sleep < 0:
            if 'sleepy' not in self.status:
                context[NARRATOR].add([self.first_name, 'needs', 'to sleep'])
                self.status.append('sleepy')
            self.add_energy(self._sleep, **context)
            self._sleep = 0
        else:
            if 'sleepy' in self.status:
                self.status.remove('sleepy')

    def consume_nutriments(self, value, **context):
        self._stomach += value
        if self._stomach < 0:
            if 'hungry' not in self.status:
                context[NARRATOR].add([self.first_name, 'needs', 'to eat'])
                self.status.append('hungry')
            self.add_energy(self._stomach, **context)
            self._stomach = 0
        else:
            if 'hungry' in self.status:
                self.status.remove('hungry')

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
            # if context[TIME] == STARTER:
            #     context[NARRATOR].new([
            #         self.name, f': {[(round(s.pref(self, **context), 2), s.name) for s in strats]}'])

    def upkeep(self, **context):
        self._water -= 0.3
        self.drink()
        energy_upkeep = -random() * 0.1  # loses energy while being awake
        sleep_upkeep = max(random(), random()) * 0.1
        food_upkeep = max(random(), random()) * 0.2
        if self.thirst > 1:
            self.status.append('thirsty')
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
            if self.be_damaged(max(0.05, self.health/5), **context):
                context[NARRATOR].add([self.first_name, 'bleeds', 'to death'])
        self._rage = 0

    def act(self, **context):
        if FLEEING in self.status:
            self.status.remove(FLEEING)
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

    def check_bag(self, **context):
        if 'unchecked bag' in self.status:
            self.status.remove('unchecked bag')
            bags = [e for e in self._equipment if isinstance(e, Bag)]
            if not len(bags):
                return
            stuff = [e.name for bag in bags for e in bag.content]
            if len(stuff):
                context[NARRATOR].new([
                    self.first_name, 'checks', self.his, 'bags,' if len(bags) > 1 else 'bag,',
                    'finds', format_list(stuff)])
            else:
                context[NARRATOR].new([
                    self.first_name, 'checks', self.his, 'bags,' if len(bags) > 1 else 'bag,',
                    'finds', 'they are' if len(bags) > 1 else 'it is', 'empty'])
            for i in range(1, len(bags)):
                extra_bag = bags[i]
                self._equipment.remove(extra_bag)
                bags[0].content.extend(extra_bag.content)
            bag_weapons = [
                i for i in bags[0].content if isinstance(i, Weapon) and i.damage_mult > self.weapon.damage_mult]
            bag_weapons.sort(key=lambda x: -x.damage_mult)
            if len(bag_weapons):
                bags[0].content.remove(bag_weapons[0])
                self.get_weapon(bag_weapons[0], **context)

    def can_flee(self, **context):
        return self.energy > self.move_cost or self.current_area != START_AREA

    def flee(self, panic=False, **context):
        self.status.append(FLEEING)
        if panic and random() > self.courage(**context) + 0.5:
            self.drop_weapon(True, **context)
        min_player_per_area = min([len(area) for key, area in context[MAP].areas.items() if key != START_AREA])
        # can't flee to or hide at the cornucopea
        best_areas = [
            key for key, value in context[MAP].areas.items() if len(value) == min_player_per_area and key != START_AREA
        ]
        best_areas.sort(key=lambda x: -len(context[MAP].loot[x]))
        best_area = best_areas[0]
        out = self.go_to(best_area, **context, **{PANIC: True})
        if out is not None:
            context[NARRATOR].add([self.first_name, f'flees to {out}'])
            self.check_for_ambush_and_traps(**context)

    def pursue(self, **context):
        max_player_per_area = max([len(area) for area in context[MAP].areas.values()])
        best_areas = [key for key, value in context[MAP].areas.items() if len(value) == max_player_per_area]
        best_areas.sort(key=lambda x: -len(context[MAP].loot[x]))
        best_area = best_areas[0]
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

    def rest(self, **context):
        if self.current_area != START_AREA:
            self.stealth += random() * (1 - self.stealth)
            context[NARRATOR].add([self.first_name, 'hides', f'at {self.current_area}'])

        self.check_bag(**context)
        self.fill_bottles(**context)
        wounds = self.wounds
        if BLEEDING in wounds:
            self.patch_bleeding(**context)
        elif len(wounds):
            self.patch_wound(context, wounds)
        else:
            self.add_health(max(self.energy, random()) * (self.max_health - self.health))
            self.add_energy(max(self.sleep, random()) * (1 - self.energy))
            context[NARRATOR].add([self.first_name, 'rests', f'at {self.current_area}'])

        if self.current_area == START_AREA:
            if self.has_food and self.hunger > 0:
                self.dine(**context)

    def patch_wound(self, context, wounds):
        tool = 'bandages' if self.has_item('bandages') else choice(['moss', 'cloth'])
        if tool != 'bandages':
            self._max_health *= 0.95
            # TODO: infection
        pick_wound = choice(wounds)
        context[NARRATOR].add([self.first_name, 'patches', self.his, pick_wound, 'using', tool])
        self.status.remove(pick_wound)

    def patch_bleeding(self, **context):
        tool = 'bandages' if self.has_item('bandages') else choice(['moss', 'cloth'])
        if tool != 'bandages':
            self._max_health *= 0.95
        context[NARRATOR].add([self.first_name, 'stops', self.his, 'wounds', 'from bleeding', 'using', tool])
        self.status.remove(BLEEDING)

    def go_to_sleep(self, **context):
        if self.energy < 0.2:
            context[NARRATOR].add([self.first_name, 'is exhausted'])
        self.add_health(self.energy * (1 - self.health), **context)
        self.add_energy(self.sleep * (1 - self.energy), **context)
        self.add_sleep(1, **context)
        context[NARRATOR].add([self.first_name, 'sleeps', f'at {self.current_area}'])
        self.status.append(SLEEPING)

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

    def check_for_ambush_and_traps(self, **context):
        traps = context[MAP].traps[self.current_area]
        for t in traps:
            if t.check(self, **context):
                t.apply(self, **context)
                return True
        ambushers = [p for p in context[MAP].neighbors(self) if AMBUSH in p.status and not SLEEPING in p.status]
        if not len(ambushers):
            return False
        ambusher = choice(ambushers)
        ambusher.status.remove(AMBUSH)
        context[NARRATOR].new([self.first_name, 'falls', 'into', f'{ambusher.first_name}\'s ambush!'])
        ambusher.fight(self, **context)
        return True

# CRAFTING
    @property
    def has_crafting_tool(self):
        if self.weapon.name in ['knife', 'hatchet']:
            return self.weapon
        tools = [i for i in self.equipment if i.name in ['knife', 'hatchet']]
        if len(tools):
            return tools[0]
        return None

    def craft(self, **context):
        self.check_bag(**context)
        self.fill_bottles(**context)
        self.craft_weapon(**context)

    def craft_weapon(self, **context):
        crafting_tool = self.has_crafting_tool
        with_tool = '' if crafting_tool is None else f'with {self.his} {crafting_tool.name}'
        name = choice(['spear', 'club'])
        weapon = Weapon(name, 1 + random() + (random() if crafting_tool is not None else 0))
        if weapon.damage_mult > self.weapon.damage_mult:
            description = weapon.long_name
            if weapon.name == self.weapon.name:
                self.weapon.long_name = f'{self.first_name}\'s old {self.weapon.name}'
                description = f'a better {weapon.name}'
            context[NARRATOR].add([self.first_name, 'crafts', description, with_tool, f'at {self.current_area}'])
            self.get_weapon(weapon, **context)
        else:
            context[NARRATOR].add([
                self.first_name, 'tries to craft a better weapon', f'at {self.current_area}'])

# EQUIPMENT
    def loot(self, **context):
        self.check_bag(**context)
        self.fill_bottles(**context)
        item = context[MAP].pick_item(self.current_area)
        if item is None or (isinstance(item, Weapon) and item.damage_mult <= self.weapon.damage_mult):
            context[NARRATOR].add([
                self.first_name, 'tries to loot', f'at {self.current_area}', 'but can\'t find anything useful'])
            return
        if isinstance(item, Weapon):
            self.loot_weapon(item, **context)
        else:
            context[NARRATOR].add([self.first_name, 'picks up', item.long_name, f'at {self.current_area}'])
            self.get_item(item, **context)

    def estimate_of_power(self, area, **context) -> float:
        neighbors = context[MAP].neighbors(self, area)
        if not len(neighbors):
            return 0
        seen_neighbors = [p for p in neighbors if random() * self.wisdom > p.stealth]
        return sum([p.dangerosity(**context) for p in seen_neighbors])

    def loot_cornucopea(self, **context):
        out = self.go_to(START_AREA, **context)
        if out is not None:
            context[NARRATOR].add([self.first_name, f'goes to {out}'])
        if self.check_for_ambush_and_traps(**context):
            return
        neighbors = context[MAP].neighbors(self)
        if not len(neighbors):
            self.loot(**context)
            return
        seen_neighbors = [p for p in neighbors if random() * self.wisdom > p.stealth]
        if sum([p.dangerosity(**context) for p in seen_neighbors]) > self.dangerosity(**context):
            context[NARRATOR].add([self.first_name, 'sees', format_list([p.first_name for p in neighbors])])
            self.flee(**context)
        elif len(seen_neighbors):
            self.attack_at_random(**context)
        else:
            self.loot(**context)

    def loot_weapon(self, weapon: Optional[Weapon]=None, **context):
        if weapon is None:
            weapon = context[MAP].pick_weapon(self.current_area)
        if weapon is None or (weapon.damage_mult <= self.weapon.damage_mult and (
                    not weapon.small or context[TIME] == STARTER or self.bag is None)):
            context[NARRATOR].add([
                self.first_name, 'tries to loot', f'at {self.current_area}', 'but can\'t find anything useful'])
            return
        if weapon.name == self.weapon.name:
            self.weapon.long_name.replace('\'s', '\'s old')
            context[NARRATOR].add([
                self.first_name, 'picks up', f'a better {weapon.name}', f'at {self.current_area}'])
        else:
            context[NARRATOR].add([self.first_name, 'picks up', weapon.long_name, f'at {self.current_area}'])
        self.get_weapon(weapon, **context)

    def loot_bag(self, **context):
        item = context[MAP].pick_bag(self.current_area)
        if item is None:
            return self.loot(**context)
        context[NARRATOR].add([self.first_name, 'picks up', item.long_name, f'at {self.current_area}'])
        self.get_item(item, **context)

    def estimate(self, item: Union[Item, List[Item]], **content) -> float:
        if isinstance(item, Item):
            if isinstance(item, Weapon):
                return item.damage_mult - self.weapon.damage_mult
            else:
                return 0
        elif len(item):
            return max([self.estimate(i) for i in list(item)])
        else:
            return 0

    def get_weapon(self, weapon, **context):
        if weapon.damage_mult > self.weapon.damage_mult:
            if self.weapon.small and self.bag is not None:
                self.bag.content.append(self.weapon)
            else:
                self.drop_weapon(verbose=False, **context)
            self.weapon = weapon
            self.weapon.long_name = f'{self.first_name}\'s {weapon.name}'
        elif weapon.small and self.bag is not None:
            self.bag.content.append(weapon)

    def drop_weapon(self, verbose=True, **context):
        if self.weapon != HANDS:
            if verbose:
                context[NARRATOR].add([
                    self.first_name, 'drops', f'{self.his} {self.weapon.name}', f'at {self.current_area}'])
            context[MAP].add_loot(self.weapon, self.current_area)
        self.weapon = HANDS

    def get_item(self, item, **context):
        if isinstance(item, Bag):
            item.long_name = f'{self.first_name}\'s {item.name}'
            if 'unchecked bag' not in self.status:
                self.status.append('unchecked bag')
            self._equipment.append(item)
        else:
            if self.bag is not None:
                self.bag.content.append(item)
            else:
                self._equipment.append(item)

    def remove_item(self, item, **context):
        if item in self._equipment:
            self._equipment.remove(item)
            return
        for b in [e for e in self._equipment if isinstance(e, Bag)]:
            if item in b.content:
                b.content.remove(item)
                return
        raise KeyError(f'no {item.name} in {self.name}\'s stash')

    def pillage(self, stuff, **context):
        if len([p for p in context[PLAYERS] if p.is_alive]) == 1:
            return
        if context[MAP].neighbors_count(self) > 1:
            return
        looted = []
        for item in stuff:
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

    @property
    def bottles(self):
        return [i for i in self.equipment if isinstance(i, Bottle)]

    def fill_bottles(self, **context):
        self.drink()
        if self.current_area == 'the river':
            total_water = self.water + sum(b.fill for b in self.bottles)
            self._water = 1
            for b in self.bottles:
                b.fill = 1
            new_total_water = self.water + sum(b.fill for b in self.bottles)
            if new_total_water > total_water + 1:
                if len(self.bottles):
                    context[NARRATOR].add([
                        self.name, 'fills', self.his, 'bottles' if len(self.bottles) > 1 else 'bottle',
                        f'at {self.current_area}'])
                else:
                    context[NARRATOR].add([self.name, 'drinks', f'at {self.current_area}'])
        else:
            water = random()
            amount = min(self.thirst, water)
            self._water += amount
            water -= amount
            for b in self.bottles:
                amount = min(1 - b.fill, water)
                b.fill += amount
                water -= amount

    def drink(self):
        if self.thirst:
            for b in self.bottles:
                amount = min(self.thirst, b.fill)
                self._water += amount
                b.fill -= amount
            if self.water and 'thirsty' in self.status:
                self.status.remove('thirsty')

# EATING
    def forage(self, **context):
        food: Food = context[MAP].get_forage(self)
        self.fill_bottles()
        if food is None:
            context[NARRATOR].add([self.name, 'searches for food', 'but does not find anything edible'])
            return
        else:
            if food.value <= self.hunger:
                context[NARRATOR].add([self.name, 'finds'])
                self.eat(food, quantifier='some', **context)
            else:
                context[NARRATOR].add([self.name, 'finds', 'some', food.name, f'at {self.current_area}'])
                food.value *= 2
            self.get_item(food, **context)  # some extras / all of it

    @property
    def has_food(self):
        return len([e for e in self.equipment if isinstance(e, Food)]) > 0

    def dine(self, **context):
        self.check_bag(**context)
        self.fill_bottles(**context)
        if not self.has_food:
            context[NARRATOR].add([self.name, 'does not have', 'anything to eat'])
        else:
            foods = [e for e in self.equipment if isinstance(e, Food)]
            foods.sort(key=lambda x: x.value)
            while self.hunger > 0 and len(foods):
                meal = foods.pop()
                self.remove_item(meal)
                self.eat(meal, quantifier=self.his, **context)

    def eat(self, food: Food, quantifier, **context):
        context[NARRATOR].add([self.name, 'eats', quantifier, food.name, f'at {self.current_area}'])
        self.consume_nutriments(food.value)

# FIGHTING
    def attack_at_random(self, **context):
        preys = [p for p in context[MAP].areas[self.current_area] if random() * self.wisdom > p.stealth and p != self]
        preys.sort(key=lambda x: x.health * x.damage(**context))
        if len(preys):
            self.fight(preys[0], **context)
        else:
            self.pursue(**context)

    def fight(self, other_player, **context):
        self.busy = True
        other_player.busy = True
        self.relationship(other_player).allied = False
        other_player.relationship(self).allied = False

        verb = 'catches and attacks' if FLEEING in other_player.status else 'attacks'
        if FLEEING in other_player.status:
            other_player.status.remove(FLEEING)
        weapon = f'with {self.his} {self.weapon.name}'
        self_stuff = []
        other_weapon = f'with {other_player.his} {other_player.weapon.name}'
        other_stuff = []
        area = f'at {self.current_area}'
        surprise_mult = 2 if SLEEPING in other_player.status else (
            1.5 if random() + self.stealth > other_player.wisdom else 1)
        surprise = f'in {other_player.his} sleep' if SLEEPING in other_player.status else (
            'by surprise' if surprise_mult > 1 else '')
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
                    other_stuff = other_stuff if other_player.weapon == HANDS else []
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
                    self_stuff = self_stuff if self.weapon == HANDS else []
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

    def hit(self, target, mult=1, **context) -> bool:
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
            return target.be_damaged(
                self.damage(**context) * mult, weapon=self.weapon.name, attacker_name=self.first_name, **context)
        else:  # Miss
            self._rage -= 0.1
            context[NARRATOR].stock([self.first_name, 'misses'])
            return False

    def damage(self, **context):
        mult = 1
        if ARM_WOUND in self.status:
            mult -= 0.2
        return mult * self.weapon.damage_mult * random() / 2

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
        self.drop_weapon(False, **context)
        for e in self._equipment:
            context[MAP].add_loot(e, self.current_area)
        context[DEATH](self, **context)


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
    lambda x, **c: (len(x.wounds) + 1) * (1 - x.health / 2) * (
        1 - min(x.energy, x.sleep)) / c[MAP].neighbors_count(x) + 0.1,
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
    lambda x, **c: (x.health if len(c[PLAYERS]) > c[MAP].neighbors_count(x) else 1) * sum([
        x.weapon.damage_mult * x.health > n.weapon.damage_mult * n.health for n in c[MAP].neighbors(x)
    ]),
    lambda x, **c: x.attack_at_random(**c))
loot_strat = Strategy(
    'loot',
    lambda x, **c: (x.energy - x.move_cost) * (2 if x.weapon.damage_mult == 1 else 0.2) *
                   x.estimate(c[MAP].loot[x.current_area], **c),
    lambda x, **c: x.loot(**c))
loot_cornucopea_strat = Strategy(
    'loot cornucopea',
    lambda x, **c: (x.energy - x.move_cost) * max(x.hunger, 3 - x.weapon.damage_mult) *
                   x.estimate(c[MAP].loot[START_AREA], **c) * (x.current_area != START_AREA) *
                   (x.dangerosity(**c) >= x.estimate_of_power(START_AREA, **c)),
    lambda x, **c: x.loot_cornucopea(**c))
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

start_strategies = [
    flee_strat, fight_strat, loot_bag_strat, loot_weapon_strat,
]

morning_strategies = [
    hide_strat, flee_strat, attack_strat, loot_strat, craft_strat_1, forage_strat, dine_strat, loot_bag_strat,
    hunt_player_strat, ambush_strat, loot_cornucopea_strat, trap_strat,
]

night_strategies = [
    hide_strat, flee_strat, loot_strat, craft_strat_2, forage_strat, dine_strat, hunt_player_strat, ambush_strat,
    loot_cornucopea_strat, trap_strat,
]
