from random import random
from typing import Dict


class Player:
    def __init__(self, first_name: str, district: int):
        self.first_name = first_name
        self.district = district
        self.relationships: Dict[Player, Relationship] = {}
        self.busy = False

    @property
    def name(self):
        return self.first_name

    def relationship(self, other_player):
        if other_player not in self.relationships:
            self.relationships[other_player] = Relationship()
        return self.relationships[other_player]

    def interact(self, other_player):
        if self.relationship(other_player).allied:
            self.relationship(other_player).friendship += random() / 10 - 0.025
            if random() > self.relationship(other_player).friendship:
                print(f'{self.first_name} betrays {other_player.first_name}')
                return self.fight(other_player)
        if random() < self.relationship(other_player).friendship:
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
            self.relationship(other_player).friendship -= random() / 10
            other_player.relationship(self).friendship -= random() / 10
            self.busy = True
            other_player.busy = True
            self.relationship(other_player).allied = False
            other_player.relationship(self).allied = False


class Relationship:
    def __init__(self):
        self.friendship = 0
        self.allied = True
