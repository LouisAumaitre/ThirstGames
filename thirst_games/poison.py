from random import random, randint

from thirst_games.abstract.entity import LivingEntity
from thirst_games.abstract.items import AbstractPoison, Item
from thirst_games.narrator import Narrator


class Poison(AbstractPoison):
    def __init__(self, name, amount, damage):
        self.name = name
        self.long_name = 'the ' + name
        self.amount = amount
        self.damage = damage

    def upkeep(self, player: LivingEntity):
        if self.amount == 0:
            player.remove_poison(self)
            return
        self.amount -= 1
        live = player.is_alive
        player.add_health(-self.damage)
        if live and not player.is_alive:
            Narrator().new([player.name, 'succumbs', 'to', self.long_name])

    def __str__(self):
        return f'{self.name}({int(self.damage * 100)}x{self.amount})'


class Food(Item):
    def __init__(self, name, value):
        Item.__init__(self, name)
        self.value = value
        self.poison = None
        if self.name in ['berries', 'fruits', 'mushrooms'] and random() > 0.8:
            self.poison = Poison(f'{self.name}\' poison', randint(3, 9), random() / 10 + 0.05)

    @property
    def is_poisonous(self):
        return self.poison is not None
