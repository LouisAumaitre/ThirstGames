from random import random, choice
from typing import Dict, List, Union

from thirst_games.constants import MAP, PLAYERS, DEATH, TIME, NARRATOR, PANIC, SLEEPING, NIGHT
from thirst_games.items import HANDS, Weapon, Item
from thirst_games.map import START_AREA

MOVE_COST = 0.3


class Player:
    def __init__(self, first_name: str, district: int, his='their'):
        self.first_name = first_name
        self.district = district
        self.his = his
        self.relationships: Dict[Player, Relationship] = {}
        self.busy = False
        self._health = 1
        self._energy = 1
        self._sleep = 1
        self.stealth = 0
        self.wisdom = 0.9
        self.equipement: List[Item] = []
        self.status = []

        self.strategy = None
        self.current_area = None
        self.weapon = HANDS

    @property
    def name(self):
        return self.first_name

    @property
    def courage(self):
        return self.health * self.energy

    @property
    def is_alive(self):
        return self.health > 0

    @property
    def energy(self):
        return max(0, self._energy)

    def add_energy(self, amount):
        self._energy = max(0, min(1, self._energy + amount))

    @property
    def health(self):
        return max(0, self._health)

    def add_health(self, amount):
        self._health = max(0, min(1, self._health + amount))

    @property
    def sleep(self):
        return max(0, self._sleep)

    def add_sleep(self, amount):
        self._sleep = max(0, min(1, self._sleep + amount))

    def relationship(self, other_player):
        if other_player not in self.relationships:
            self.relationships[other_player] = Relationship()
        return self.relationships[other_player]

    def think(self, **context):
        if SLEEPING in self.status:
            self.status.remove(SLEEPING)
        else:
            upkeep = max(random(), random()) * 0.2
            self.add_energy(min(upkeep, self.sleep))
            self.add_sleep(-upkeep)

        if self.sleep < 0:
            if context[MAP].neighbors_count(self) > 1 and self.energy > MOVE_COST:
                self.strategy = flee_strat
            else:
                self.strategy = hide_strat
        elif context[TIME] == NIGHT:
            night_strategies.sort(key=lambda x: -x.pref(self, **context) + random() * (1 - self.wisdom))
            self.strategy = night_strategies[0]
        else:
            morning_strategies.sort(key=lambda x: -x.pref(self, **context))
            self.strategy = morning_strategies[0]
            # context[NARRATOR].new([
            #     self.name, f': {[(round(s.pref(self, **context), 2), s.name) for s in morning_strategies]}'])

    def act(self, **context):
        context[NARRATOR].cut()
        if not self.busy:
            self.strategy.apply(self, **context)
        context[NARRATOR].cut()
        self.strategy = None

    def flee(self, panic=False, **context):
        if panic and random() > self.courage + 0.5:
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

    def pursue(self, **context):
        max_player_per_area = max([len(area) for area in context[MAP].areas.values()])
        best_areas = [key for key, value in context[MAP].areas.items() if len(value) == max_player_per_area]
        best_areas.sort(key=lambda x: -len(context[MAP].loot[x]))
        best_area = best_areas[0]
        out = self.go_to(best_area, **context)
        if out is None:
            context[NARRATOR].replace('hides and rests', 'rests')
        else:
            context[NARRATOR].add([self.first_name, 'goes hunting', f'at {out}'])

    def go_to(self, area, **context):
        if area != self.current_area and self.energy >= MOVE_COST:
            self.reveal()
            self._energy -= MOVE_COST
            self.busy = True
            return context[MAP].move_player(self, area)
        else:
            self._energy -= MOVE_COST
            self.hide(**context)

    def hide(self, **context):
        if context.get(PANIC, False):
            context[NARRATOR].add([self.first_name, 'hides', f'at {self.current_area}'])
            return
        if self.sleep < 0.1 \
                or (context[TIME] == NIGHT and context[MAP].neighbors_count == 1) \
                or (context[MAP].neighbors_count == 1 and self.sleep < 0.2) \
                or (context[TIME] == NIGHT and self.sleep < 0.3):
            self.go_to_sleep(**context)
            return
        if self.current_area == START_AREA:
            self.add_health(max(self.energy, random()) * (1 - self.health))
            self.add_energy(max(self.sleep, random()) * (1 - self.energy))
            context[NARRATOR].add([self.first_name, 'rests', f'at {self.current_area}'])
        else:
            self.stealth += random() * (1 - self.stealth)
            self.add_health(max(0, min(self.energy, random())) * (1 - self.health))
            self.add_energy(max(0, min(self.sleep, random())) * (1 - self.energy))
            context[NARRATOR].add([self.first_name, 'hides and rests', f'at {self.current_area}'])

    def go_to_sleep(self, **context):
        if self.energy < 0.2:
            context[NARRATOR].add([self.first_name, 'is exhausted'])
        self.add_health(self.energy * (1 - self.health))
        self.add_energy(self.sleep * (1 - self.energy))
        self.add_sleep(1)
        context[NARRATOR].add([self.first_name, 'sleeps', f'at {self.current_area}'])
        self.status.append(SLEEPING)

    def loot(self, **context):
        item = context[MAP].pick_item(self.current_area)
        if item is None or (isinstance(item, Weapon) and item.damage_mult <= self.weapon.damage_mult):
            context[NARRATOR].add([
                self.first_name, 'tries to loot', f'at {self.current_area}', 'but can\'t find anything useful'])
            return
        if isinstance(item, Weapon):
            weapon: Weapon = item
            if weapon.name == self.weapon.name:
                self.weapon.long_name.replace('\'s', '\'s old')
                context[NARRATOR].add([
                    self.first_name, 'picks up', f'a better {weapon.name}', f'at {self.current_area}'])
            else:
                context[NARRATOR].add([self.first_name, 'picks up', weapon.long_name, f'at {self.current_area}'])
            self.get_weapon(weapon, **context)
        else:
            self.equipement.append(item)
            context[NARRATOR].add([self.first_name, 'picks up', item.long_name, f'at {self.current_area}'])

    def craft(self, **context):
        name = choice(['spear', 'club'])
        weapon = Weapon(name, 1 + random())
        if weapon.damage_mult > self.weapon.damage_mult:
            if weapon.name == self.weapon.name:
                self.weapon.long_name.replace('\'s', '\'s old')
                context[NARRATOR].add([self.first_name, 'crafts', f'a better {weapon.name}', f'at {self.current_area}'])
            else:
                context[NARRATOR].add([self.first_name, 'crafts', f'a {weapon.name}', f'at {self.current_area}'])
            self.get_weapon(weapon, **context)
        else:
            context[NARRATOR].add([
                self.first_name, 'tries to craft a better weapon', f'at {self.current_area}'])

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
        self.drop_weapon(False, **context)
        self.weapon = weapon
        self.weapon.long_name = f'{self.first_name}\'s {weapon.name}'

    def attack_at_random(self, **context):
        preys = [p for p in context[MAP].areas[self.current_area] if random() > p.stealth and p != self]
        preys.sort(key=lambda x: x.health)
        if len(preys):
            self.fight(preys[0], **context)
        else:
            self.pursue(**context)

    def reveal(self):
        self.stealth = 0

    def interact(self, other_player, **context):
        if random() < other_player.stealth:
            return
        if self.relationship(other_player).allied:
            self.relationship(other_player).friendship += random() / 10 - 0.025
            if random() > self.relationship(other_player).friendship or len(context[PLAYERS]) < 3:
                print(f'{self.first_name} betrays {other_player.first_name}')
                return self.fight(other_player, context)
        # elif random() < self.relationship(other_player).friendship and len(context[PLAYERS]) > 3:
        #     if random() < other_player.relationship(self).friendship:
        #         print(f'{self.first_name} makes an alliance with {other_player.first_name}')
        #         self.relationship(other_player).friendship += random() / 10
        #         other_player.relationship(self).friendship += random() / 10
        #         self.busy = True
        #         other_player.busy = True
        #         self.relationship(other_player).allied = True
        #         other_player.relationship(self).allied = True
        #     else:
        #         print(f'{self.first_name} tries to make an alliance with {other_player.first_name},'
        #               f' but {other_player.first_name} refuses')
        #         self.relationship(other_player).friendship -= random() / 10
        #         self.busy = True
        #         other_player.busy = True
        elif random() < -self.relationship(other_player).friendship:
            self.fight(other_player, context)
        else:
            self.relationship(other_player).friendship += random() / 10 - 0.05

    def hit(self, target, mult=1, **context) -> bool:
        self.add_energy(-0.2)
        return target.be_damaged(self.damage(**context) * mult, **context)

    def fight(self, other_player, **context):
        self.reveal()
        other_player.reveal()
        self.relationship(other_player).friendship -= random() / 10
        other_player.relationship(self).friendship -= random() / 10
        self.busy = True
        other_player.busy = True
        self.relationship(other_player).allied = False
        other_player.relationship(self).allied = False

        verb = 'attacks'
        weapon = f'with {self.his} {self.weapon.name}'
        y_weapon = self.weapon
        other_weapon = f'with {other_player.his} {other_player.weapon.name}'
        t_weapon = other_player.weapon
        area = f'at {self.current_area}'
        surprise = f'in {other_player.his} sleep' if SLEEPING in other_player.status else 'by surprise'
        surprise_mult = 2 if SLEEPING in other_player.status else 1 + self.wisdom - other_player.wisdom

        if self.hit(other_player, surprise_mult, **context):
            context[NARRATOR].add([
                self.first_name, 'kills', other_player.first_name, surprise, area, weapon])
        else:
            while True:
                if random() > other_player.courage:
                    context[NARRATOR].add([self.first_name, verb, other_player.first_name, area, weapon])
                    other_player.flee(True, **context)
                    break
                if other_player.hit(self, **context):
                    context[NARRATOR].add([
                        other_player.first_name, 'kills', self.first_name, area, 'in self-defense', other_weapon])
                    break
                verb = 'fights'
                if random() > self.courage:
                    context[NARRATOR].add([self.first_name, 'attacks', other_player.first_name, area, weapon])
                    context[NARRATOR].add([
                        other_player.first_name, 'fights back', other_weapon, 'and'])
                    self.flee(True, **context)
                    break
                if self.hit(other_player, **context):
                    context[NARRATOR].add([self.first_name, f'{verb} and kills', other_player.first_name, area, weapon])
                    break
        if other_player.weapon == HANDS and t_weapon != HANDS:
            self.pillage(t_weapon, **context)
        elif self.weapon == HANDS and y_weapon != HANDS:
            other_player.pillage(y_weapon, **context)

    def pillage(self, weapon, **context):
        if weapon.damage_mult > self.weapon.damage_mult:
            context[NARRATOR].add([self.first_name, 'loots', weapon.long_name])
            context[MAP].remove_loot(weapon, self.current_area)
            self.get_weapon(weapon, **context)

    def damage(self, **context):
        return self.weapon.damage_mult * random() / 2

    def be_damaged(self, damage, **context) -> bool:
        if self.health < 0:
            print(f'{self.first_name} is already dead')
            return False
        self.add_health(-damage)
        if self.health <= 0:
            self.die(**context)
            return True
        return False

    def die(self, **context):
        self.drop_weapon(False, **context)
        for e in self.equipement:
            context[MAP].add_loot(e, self.current_area)
        context[DEATH](self, **context)

    def drop_weapon(self, verbose=True, **context):
        if self.weapon != HANDS:
            if verbose:
                context[NARRATOR].add([
                    self.first_name, 'drops', f'{self.his} {self.weapon.name}', f'at {self.current_area}'])
            context[MAP].add_loot(self.weapon, self.current_area)
        self.weapon = HANDS


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
    lambda x, **c: (c[MAP].neighbors_count(x) == 1 or x.current_area != START_AREA) *
                   (1 - x.health) * (1 - min(x.energy, x.sleep)) / c[MAP].neighbors_count(x),
    lambda x, **c: x.hide(**c))
flee_strat = Strategy(
    'flee',
    lambda x, **c: (x.energy - 0.3) * (1 - x.health / 2) * (1 + sum([
        n.weapon.damage_mult > x.weapon.damage_mult for n in c[MAP].neighbors(x)
    ])) * c[MAP].neighbors_count(x) / 6 * x.energy * (c[MAP].neighbors_count(x) > x.courage * 10),
    lambda x, **c: x.flee(**c))
fight_strat = Strategy(
    'fight',
    lambda x, **c: (x.health - 0.5) * (x.energy - 0.3) * x.weapon.damage_mult / c[MAP].neighbors_count(x),
    lambda x, **c: x.attack_at_random(**c))
loot_strat = Strategy(
    'loot',
    lambda x, **c: (x.energy - 0.3) * (2 if x.weapon.damage_mult == 1 else 0.2) *
                   x.estimate(c[MAP].loot[x.current_area], **c),
    lambda x, **c: x.loot(**c))
craft_strat_1 = Strategy(
    'craft',
    lambda x, **c: (x.energy - 0.2) * (2 - x.weapon.damage_mult) * (c[MAP].neighbors_count(x) < 2),
    lambda x, **c: x.craft(**c))
craft_strat_2 = Strategy(
    'craft',
    lambda x, **c: (x.energy - 0.2) * (x.weapon.damage_mult < 2) *
                   (2 - x.weapon.damage_mult) / c[MAP].neighbors_count(x),
    lambda x, **c: x.craft(**c))

morning_strategies = [
    hide_strat, flee_strat, fight_strat, loot_strat, craft_strat_1,
]

night_strategies = [
    hide_strat, flee_strat, loot_strat, craft_strat_2,
]
