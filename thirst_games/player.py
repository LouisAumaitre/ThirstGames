from copy import copy
from random import random
from typing import Dict

from thirst_games.constants import MAP, PLAYERS, DEATH, TIME, MORNING


class Player:
    def __init__(self, first_name: str, district: int):
        self.first_name = first_name
        self.district = district
        self.relationships: Dict[Player, Relationship] = {}
        self.busy = False
        self.health = 1
        self.energy = 1
        self.stealth = 0
        self.status = []

        self.strategy = None
        self.current_area = None

    @property
    def name(self):
        return self.first_name

    @property
    def is_alive(self):
        return self.health > 0

    def relationship(self, other_player):
        if other_player not in self.relationships:
            self.relationships[other_player] = Relationship()
        return self.relationships[other_player]

    def think(self, context):
        if context[TIME] == MORNING:
            morning_strategies.sort(key=lambda x: -x.pref(self, context))
            self.strategy = morning_strategies[0]
        else:
            afternoon_strategies.sort(key=lambda x: -x.pref(self, context))
            self.strategy = afternoon_strategies[0]

    def act(self, context):
        self.strategy.apply(self, context)

    def act_alone(self, context: Dict):
        if self.health < 0.5:
            if self.energy > 0.2:
                self.flee(context)
            else:
                self.hide(context)

    def flee(self, context):
        min_player_per_area = min([len(area) for area in context[MAP].areas.values()])
        best_area = [key for key, value in context[MAP].areas.items() if len(value) == min_player_per_area][0]
        self.go_to(context[MAP], best_area)

    def pursue(self, context):
        max_player_per_area = max([len(area) for area in context[MAP].areas.values()])
        best_area = [key for key, value in context[MAP].areas.items() if len(value) == max_player_per_area][0]
        self.go_to(context[MAP], best_area)

    def go_to(self, map_, area):
        if self.energy >= 0.2:
            map_.move_player(self, area)
            self.reveal()
            self.energy -= 0.2
            self.busy = True

    def hide(self, context):
        print(f'{self.first_name} hides and rests')
        self.stealth += random() * (1 - self.stealth)
        self.energy += random() * (1 - self.energy)
        self.health += random() * (1 - self.health)

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

        if other_player.be_damaged(random(), context):
            print(f'{self.first_name} kills {other_player.first_name} by surprise at {self.current_area}')
        else:
            if self.be_damaged(random(), context):
                print(f'{other_player.first_name} kills {self.first_name} at {self.current_area} in self-defense')
            else:
                print(f'{self.first_name} attacks {other_player.first_name} at {self.current_area}')

    def be_damaged(self, damage, context):
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
    def __init__(self, pref, action):
        self.pref = pref
        self.action = action

    def apply(self, player, context, **kwargs):
        self.action(player, context, **kwargs)


morning_strategies = [
    Strategy(lambda x, c: (1 - x.health / 2) / c[MAP].neighbors_count(x), lambda x, c, **kw: x.hide(c)),
    Strategy(lambda x, c: (1 - x.health / 2) * c[MAP].neighbors_count(x) * x.energy, lambda x, c, **kw: x.flee(c)),
    Strategy(lambda x, c: x.health * c[MAP].neighbors_count(x) * x.energy, lambda x, c, **kw: x.attack_at_random(c)),
]

afternoon_strategies = [
    Strategy(lambda x, c: (1 - x.health / 2) / c[MAP].neighbors_count(x), lambda x, c, **kw: x.hide(c)),
    Strategy(lambda x, c: (1 - x.health / 2) * c[MAP].neighbors_count(x) * x.energy, lambda x, c, **kw: x.flee(c)),
]
