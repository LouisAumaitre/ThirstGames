from random import choice, random
from typing import List, Optional, Union

from copy import copy

from thirst_games.constants import MAP, KNIFE, HATCHET, NARRATOR, BLEEDING, TIME, STARTER, SWORD, AXE
from thirst_games.items import Bag, Item, Weapon, Bottle, Food, HANDS
from thirst_games.map import START_AREA
from thirst_games.narrator import format_list
from thirst_games.player.body import Body


class Carrier(Body):
    def __init__(self, first_name, his):
        Body.__init__(self, first_name, his)
        self._equipment: List[Item] = []
        self.weapon: Weapon = HANDS

    @property
    def equipment(self):
        bags = [e for e in self._equipment if isinstance(e, Bag)]
        return [*[e for e in self._equipment if not isinstance(e, Bag)], *[e for b in bags for e in b.content]]

    @property
    def bag(self):
        bags = [e for e in self._equipment if isinstance(e, Bag)]
        if not len(bags):
            return None
        return bags[0]

    @property
    def bottles(self):
        return [i for i in self.equipment if isinstance(i, Bottle)]

    def has_item(self, item_name):
        return item_name in [*[i.name for i in self.equipment], self.weapon.name]

    @property
    def has_crafting_tool(self):
        if self.weapon.name in [KNIFE, HATCHET]:
            return self.weapon
        tools = [i for i in self.equipment if i.name in [KNIFE, HATCHET]]
        if len(tools):
            return tools[0]
        return None

    @property
    def has_food(self):
        return len([e for e in self.equipment if isinstance(e, Food)]) > 0

    @property
    def drops(self):
        stuff = copy(self._equipment)
        if self.weapon != HANDS:
            stuff.append(self.weapon)
        return stuff

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
                context[NARRATOR].cut()
            else:
                context[NARRATOR].new([
                    self.first_name, 'checks', self.his, 'bags,' if len(bags) > 1 else 'bag,',
                    'finds', 'they are' if len(bags) > 1 else 'it is', 'empty'])
                context[NARRATOR].cut()
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

    def patch(self, wound: str, **context):
        verbs = []
        tools = []
        if self.has_item('antiseptic'):
            self.remove_item('antiseptic')
            verbs = ['disinfects']
            tools = ['anticeptic']
        elif context[MAP].has_water(self):
            self._max_health *= 0.99
            verbs = ['cleans']
            tools = [f'{self.current_area}\'s water']
        elif sum([b.fill for b in self.bottles]) > 0.2:
            self.use_water(0.2)
            self._max_health *= 0.99
            verbs = ['cleans']
            tools = ['water']
        else:
            self._max_health *= 0.95

        verbs.append('stops' if wound == BLEEDING else 'patches')
        verb_part_2 = 'from bleeding' if wound == BLEEDING else ''
        if self.has_item('bandages'):
            self.remove_item('bandages')
            tools.append('bandages')
        else:
            self._max_health *= 0.95
            tools.append(choice(['moss', 'cloth']))

        wound_name = 'wounds' if wound == BLEEDING else wound
        context[NARRATOR].add([
            self.first_name, format_list(verbs), self.his, wound_name, verb_part_2, 'using', format_list(tools)])

        self.status.remove(wound)

    def rest(self, **context):
        Body.rest(self, **context)

        if self.current_area == START_AREA:
            if self.has_food and self.hunger > 0:
                self.dine(**context)

    def upkeep(self, **context):
        Body.upkeep(self, **context)
        if self.has_item(KNIFE) or self.has_item(SWORD) or self.has_item(HATCHET) or self.has_item(AXE):
            self.free_from_trap(**context)

    def take_a_break(self, **context):
        self.check_bag(**context)
        self.consume_antidote(**context)
        self.fill_bottles(**context)

    def loot(self, **context):
        self.take_a_break(**context)
        if context[MAP].neighbors_count(self) == 1:
            item = context[MAP].pick_best_item(self)
        else:
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

    def loot_weapon(self, weapon: Optional[Weapon]=None, **context):
        if weapon is None:
            weapon = context[MAP].pick_weapon(self.current_area)
        if weapon is None or (weapon.damage_mult <= self.weapon.damage_mult and (
                    not weapon.small or context[TIME] == STARTER or self.bag is None)):
            context[NARRATOR].add([
                self.first_name, 'tries to find a weapon', f'at {self.current_area}', 'but can\'t find anything good'])
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
            elif isinstance(item, Bag):
                return len(item.content) > 0
            elif isinstance(item, Food):
                return self.hunger
            elif isinstance(item, Bottle):
                return self.thirst * item.fill
            elif item.name == 'bandages' or item.name == 'antiseptic':
                return 1 if self.wounds else 0.1
            else:
                return 0.1
        elif len(item):
            return max([self.estimate(i) for i in list(item)])
        else:
            return 0

    @property
    def has_weapon(self):
        return self.weapon != HANDS

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
        if isinstance(item, str):
            item = [i for i in self.equipment if i.name == item][0]
        if item in self._equipment:
            self._equipment.remove(item)
            return
        for b in [e for e in self._equipment if isinstance(e, Bag)]:
            if item in b.content:
                b.content.remove(item)
                return
        raise KeyError(f'no {item.name} in {self.name}\'s stash')

    def craft(self, **context):
        self.take_a_break(**context)
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

    def fill_bottles(self, **context):
        self.water_upkeep()
        if context[MAP].has_water(self):
            total_water = self.water + sum(b.fill for b in self.bottles)
            self._water = max(1.5, self.water)
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

    def water_upkeep(self):
        if self.thirst:
            for b in self.bottles:
                amount = min(self.thirst, b.fill)
                self.drink(amount)
                b.fill -= amount
        Body.water_upkeep(self)

    def use_water(self, amount) -> int:
        for b in self.bottles:
            _amount = min(amount, b.fill)
            amount -= _amount
            b.fill -= _amount
        return amount

    def forage(self, **context):
        food: Food = context[MAP].get_forage(self)
        self.fill_bottles(**context)
        if food is None:
            context[NARRATOR].add([self.name, 'searches for food', 'but does not find anything edible'])
            return
        else:
            poison = False
            if food.value <= self.hunger:
                context[NARRATOR].add([self.name, 'finds'])
                poison = self.eat(food, quantifier='some', **context) == 'poison'
            else:
                context[NARRATOR].add([self.name, 'finds', 'some', food.name, f'at {self.current_area}'])
                food.value *= 2
            if not poison:
                self.get_item(food, **context)  # some extras / all of it
            else:
                self.consume_antidote(**context)

    def dine(self, **context):
        self.take_a_break(**context)
        if not self.has_food:
            context[NARRATOR].add([self.name, 'does not have', 'anything to eat'])
        else:
            foods = [e for e in self.equipment if isinstance(e, Food)]
            foods.sort(key=lambda x: x.value)
            diner = []
            poison = None
            while self.hunger > 0 and len(foods):
                meal = foods.pop()
                self.remove_item(meal)
                diner.append(meal.name)
                if self.eat(meal, verbose=False, **context) == 'poison':
                    poison = meal
                    break
            context[NARRATOR].add([self.name, 'eats', self.his, format_list(diner), f'at {self.current_area}'])
            if poison is not None:
                context[NARRATOR].new([f'the {poison.name}', 'is', 'poisonous!'])
                context[NARRATOR].cut()
                self.consume_antidote(**context)

    def eat(self, food: Food, quantifier='', verbose=True, **context):
        if verbose:
            context[NARRATOR].add([self.name, 'eats', quantifier, food.name, f'at {self.current_area}'])
        self.consume_nutriments(food.value)
        if food.is_poisonous:
            self._poisons.append(copy(food.poison))
            while food in self.equipment:
                self.remove_item(food)
            if verbose:
                context[NARRATOR].new([f'The {food.name}', 'are' if food.name[-1] == 's' else 'is', 'poisonous!'])
                context[NARRATOR].cut()
            return 'poison'

    def consume_antidote(self, **context):
        if len(self.active_poisons) and self.has_item('antidote'):
            context[NARRATOR].new([self.first_name, 'uses', self.his, 'antidote'])
            poisons = copy(self.active_poisons)
            poisons.sort(key=lambda p: -p.damage * p.amount)
            self.remove_poison(poisons[0], **context)

    def die(self, **context):
        self.drop_weapon(False, **context)
        for e in self._equipment:
            context[MAP].add_loot(e, self.current_area)
        Body.die(self, **context)
