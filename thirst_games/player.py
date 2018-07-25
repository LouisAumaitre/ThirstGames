from random import random
from typing import Dict


class Player:
    def __init__(self, first_name: str, district: int):
        self.first_name = first_name
        self.district = district
        self.relationships: Dict[Player, Relationship] = {}
        self.busy = False
        self.health = 100
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

    def act_alone(self):
        pass

    def interact(self, other_player):
        if self.relationship(other_player).allied:
            self.relationship(other_player).friendship += random() / 10 - 0.025
            if random() > self.relationship(other_player).friendship:
                print(f'{self.first_name} betrays {other_player.first_name}')
                return self.fight(other_player)
        elif random() < self.relationship(other_player).friendship:
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
