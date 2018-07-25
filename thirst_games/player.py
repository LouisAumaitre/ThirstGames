from copy import copy
from random import random
from typing import Dict

from thirst_games.constants import MAP, PLAYERS, DEATH, TIME, MORNING
from thirst_games.items import HANDS, Weapon
from thirst_games.map import START_AREA


class Player:
    def __init__(self, first_name: str, district: int):
        self.first_name = first_name
        self.district = district
        self.relationships: Dict[Player, Relationship] = {}
        self.busy = False
        self.health = 1
        self.energy = 1
        self.stealth = 0
        self.wisdom = 0.9
        self.status = []

        self.strategy = None
        self.current_area = None
        self.weapon = HANDS

    @property
    def name(self):
        return self.first_name

    @property
    def courage(self):
        return self.health

    @property
    def is_alive(self):
        return self.health > 0

    def relationship(self, other_player):
        if other_player not in self.relationships:
            self.relationships[other_player] = Relationship()
        return self.relationships[other_player]

    def think(self, context):
        if context[TIME] == MORNING:
            morning_strategies.sort(key=lambda x: -x.pref(self, context) + random() * (1 - self.wisdom))
            # print(f'{self.name}: {[(round(s.pref(self, context), 2), s.name) for s in morning_strategies]}')
            self.strategy = morning_strategies[0]
        else:
            afternoon_strategies.sort(key=lambda x: -x.pref(self, context))
            self.strategy = afternoon_strategies[0]

    def act(self, context):
        if not self.busy:
            # print(f'{self.name} -> {self.strategy.name}')
            self.strategy.apply(self, context)

    def act_alone(self, context: Dict):
        if self.health < 0.5:
            if self.energy > 0.2:
                self.flee(context)
            else:
                self.hide(context)

    def flee(self, context):
        min_player_per_area = min([len(area) for key, area in context[MAP].areas.items()])
        best_area = [key for key, value in context[MAP].areas.items() if len(value) == min_player_per_area][0]
        out = self.go_to(context, best_area)
        if out == 'hides and rests':
            return 'hides'
        return f'flees {out}'

    def pursue(self, context):
        max_player_per_area = max([len(area) for area in context[MAP].areas.values()])
        best_area = [key for key, value in context[MAP].areas.items() if len(value) == max_player_per_area][0]
        out = self.go_to(context, best_area)
        if out == 'hides and rests':
            return 'rests'
        return f'goes {out}'

    def go_to(self, context, area):
        if area != self.current_area and self.energy >= 0.2:
            self.reveal()
            self.energy -= 0.2
            self.busy = True
            return context[MAP].move_player(self, area)
        else:
            return self.hide(context)

    def hide(self, context):
        self.stealth += random() * (1 - self.stealth)
        self.energy += random() * (1 - self.energy)
        self.health += random() * (1 - self.health)
        return 'hides and rests'

    def loot(self, context):
        if self.current_area == START_AREA and len(context[MAP].weapons) > 0:
            weapon = context[MAP].weapons.pop()
            if weapon.damage_mult > self.weapon.damage_mult:
                if weapon.name == self.weapon.name:
                    print(f'{self.name} picks up a new {weapon.name}')
                else:
                    print(f'{self.name} picks up a {weapon.name}')
                self.weapon = weapon
        else:
            print(f'{self.name} tries to loot but can\'t find anything')

    def craft(self, context):
        weapon = Weapon('stick', 1 + random())
        if weapon.damage_mult > self.weapon.damage_mult:
            if weapon.name == self.weapon.name:
                print(f'{self.name} crafts a new {weapon.name}')
            else:
                print(f'{self.name} crafts a {weapon.name}')
            self.weapon = weapon

    def attack_at_random(self, context):
        preys = [p for p in context[MAP].areas[self.current_area] if random() > p.stealth and p != self]
        preys.sort(key=lambda x: x.health)
        if len(preys):
            self.fight(preys[0], context)
        else:
            self.pursue(context)

    def reveal(self):
        self.stealth = 0

    def interact(self, other_player, context: Dict):
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

    def fight(self, other_player, context):
        self.reveal()
        other_player.reveal()
        self.relationship(other_player).friendship -= random() / 10
        other_player.relationship(self).friendship -= random() / 10
        self.busy = True
        other_player.busy = True
        self.relationship(other_player).allied = False
        other_player.relationship(self).allied = False

        verb = 'attacks'
        weapon = f' with their {self.weapon.name}'
        other_weapon = f' with their {other_player.weapon.name}'
        kill = False
        other_kill = False
        if other_player.be_damaged(self.damage(context), context):
            print(f'{self.first_name} kills {other_player.first_name} by surprise at {self.current_area}{weapon}')
            kill = True
        else:
            while True:
                if random() > other_player.courage:
                    print(f'{self.first_name} {verb} {other_player.first_name} at {self.current_area}{weapon}, '
                          f'{other_player.first_name} {other_player.flee(context)}')
                    break
                if self.be_damaged(other_player.damage(context), context):
                    print(f'{other_player.first_name} kills {self.first_name} at {self.current_area} '
                          f'in self-defense{other_weapon}')
                    other_kill = True
                    break
                verb = 'fights'
                if random() > self.courage:
                    print(f'{self.first_name} attacks {other_player.first_name} at {self.current_area}{weapon}, '
                          f'{other_player.first_name} fights back{other_weapon} '
                          f'and {self.first_name} {self.flee(context)}')
                    break
                if other_player.be_damaged(self.damage(context), context):
                    print(f'{self.first_name} {verb} and kills {other_player.first_name} '
                          f'at {self.current_area}{weapon}')
                    kill = True
                    break
        if kill:
            self.pillage(other_player)
        elif other_kill:
            other_player.pillage(self)

    def pillage(self, dead):
        if dead.weapon.damage_mult > self.weapon.damage_mult:
            self.weapon = dead.weapon
            print(f'{self.first_name} loots {dead.first_name}\'s {self.weapon.name}')

    def damage(self, context):
        return self.weapon.damage_mult * random() / 2

    def be_damaged(self, damage, context, dealer=None):
        if self.health < 0:
            print(f'{self.first_name} is already dead')
            return False
        self.health -= damage
        if self.health < 0:
            context[DEATH](self, context)
            return True
        return False


class Relationship:
    def __init__(self):
        self.friendship = 0
        self.allied = False


class Strategy:
    def __init__(self, name, pref, action):
        self.name = name
        self.pref = pref
        self.action = action

    def apply(self, player, context, **kwargs):
        out = self.action(player, context, **kwargs)
        if isinstance(out, str):
            print(f'{player.first_name} {out}')


morning_strategies = [
    Strategy('hide', lambda x, c: (1 - x.health / 2) / c[MAP].neighbors_count(x), lambda x, c, **kw: x.hide(c)),
    Strategy(
        'flee',
        lambda x, c: (1 - x.health / 2) * (1 + sum([
            n.weapon.damage_mult > x.weapon.damage_mult for n in c[MAP].neighbors(x)
        ])) * c[MAP].neighbors_count(x) / 6 * x.energy * (c[MAP].neighbors_count(x) > x.courage * 10),
        lambda x, c, **kw: x.flee(c)),
    Strategy(
        'fight',
        lambda x, c: x.health * x.energy * x.weapon.damage_mult / c[MAP].neighbors_count(x),
        lambda x, c, **kw: x.attack_at_random(c)),
    Strategy(
        'loot',
        lambda x, c: (2 if x.weapon.damage_mult == 1 else 0.1) * (
            x.current_area == START_AREA) * (len(c[MAP].weapons) > 0),
        lambda x, c, **kw: x.loot(c)),
    Strategy(
        'craft',
        lambda x, c: (2 - x.weapon.damage_mult) * (c[MAP].neighbors_count(x) < 2),
        lambda x, c, **kw: x.craft(c)),
]

afternoon_strategies = [
    Strategy('hide', lambda x, c: (1 - x.health / 2) / c[MAP].neighbors_count(x), lambda x, c, **kw: x.hide(c)),
    Strategy(
        'flee',
        lambda x, c: (1 - x.health / 2) * (1 + sum([
            n.weapon.damage_mult > x.weapon.damage_mult for n in c[MAP].neighbors(x)
        ])) * c[MAP].neighbors_count(x) / 6 * x.energy * (c[MAP].neighbors_count(x) > x.courage * 10),
        lambda x, c, **kw: x.flee(c)),
    Strategy(
        'loot',
        lambda x, c: (3 - x.weapon.damage_mult) * (x.current_area == START_AREA) * (len(c[MAP].weapons) > 0),
        lambda x, c, **kw: x.loot(c)),
    Strategy(
        'craft',
        lambda x, c: (x.weapon.damage_mult < 2) * (2 - x.weapon.damage_mult) / c[MAP].neighbors_count(x),
        lambda x, c, **kw: x.craft(c)),
]
