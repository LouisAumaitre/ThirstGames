from random import random
from typing import Dict

from thirst_games.constants import MAP, PLAYERS


class Player:
    def __init__(self, first_name: str, district: int):
        self.first_name = first_name
        self.district = district
        self.relationships: Dict[Player, Relationship] = {}
        self.busy = False
        self.health = 100
        self.energy = 100
        self.stealth = 0
        self.status = []

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

    def act_alone(self, context: Dict):
        if self.health < 50:
            if self.energy > 20:
                min_player_per_area = min([len(area) for area in context[MAP].areas.values()])
                best_area = [key for key, value in context[MAP].areas.items() if len(value) == min_player_per_area][0]
                self.go_to(context[MAP], best_area)
            else:
                self.hide(context)

    def go_to(self, map_, area):
        if self.energy >= 20:
            map_.move_player(self, area)
            self.reveal()
            self.energy -= 20

    def hide(self, context):
        print(f'{self.first_name} hides')
        self.stealth += random() * (1 - self.stealth)

    def reveal(self):
        self.stealth = 0

    def interact(self, other_player, context: Dict):
        if random() < other_player.stealth:
            return
        if self.relationship(other_player).allied:
            self.relationship(other_player).friendship += random() / 10 - 0.025
            if random() > self.relationship(other_player).friendship or len(context[PLAYERS]) < 3:
                print(f'{self.first_name} betrays {other_player.first_name}')
                return self.fight(other_player)
        elif random() < self.relationship(other_player).friendship and len(context[PLAYERS]) > 3:
            if random() < other_player.relationship(self).friendship:
                print(f'{self.first_name} makes an alliance with {other_player.first_name}')
                self.relationship(other_player).friendship += random() / 10
                other_player.relationship(self).friendship += random() / 10
                self.busy = True
                other_player.busy = True
                self.relationship(other_player).allied = True
                other_player.relationship(self).allied = True
            else:
                print(f'{self.first_name} tries to make an alliance with {other_player.first_name},'
                      f' but {other_player.first_name} refuses')
                self.relationship(other_player).friendship -= random() / 10
                self.busy = True
                other_player.busy = True
        elif random() < -self.relationship(other_player).friendship:
            print(f'{self.first_name} attacks {other_player.first_name}')
            self.fight(other_player)
        else:
            self.relationship(other_player).friendship += random() / 10 - 0.05

    def fight(self, other_player):
            self.reveal()
            other_player.reveal()
            self.relationship(other_player).friendship -= random() / 10
            other_player.relationship(self).friendship -= random() / 10
            self.busy = True
            other_player.busy = True
            self.relationship(other_player).allied = False
            other_player.relationship(self).allied = False

            other_player.be_damaged(random() * 100, f'{self.first_name} kills {other_player.first_name}')
            if other_player.health > 0:
                self.be_damaged(random() * 100, f'{other_player.first_name} kills {self.first_name}')

    def be_damaged(self, damage, death_text):
        if self.health < 0:
            print(f'{self.first_name} is already dead')
        self.health -= damage
        if self.health < 0:
            print(death_text)


class Relationship:
    def __init__(self):
        self.friendship = 0
        self.allied = False
