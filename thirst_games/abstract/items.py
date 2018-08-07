from typing import Optional

from random import random, randint

from thirst_games.narrator import format_list
from thirst_games.poison import Poison


class Item:
    def __init__(self, name):
        self.name = name
        self.long_name = 'a ' + name if name[0] not in ['a', 'e', 'i', 'o', 'u'] else 'an ' + name
        if name[-1] == 's':
            self.long_name = name

    def __str__(self):
        return self.name


class Weapon(Item):
    def __init__(self, name, damage_mult):
        Item.__init__(self, name)
        self.damage_mult = damage_mult
        self.small = name in ['hatchet', 'knife']
        self.poison: Optional[Poison] = None

    def __str__(self):
        if self.poison is not None:
            return f'{self.name}({self.poison})'
        return self.name


HANDS = Weapon('bare hands', 1)


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


class Bag(Item):
    def __init__(self, content):
        Item.__init__(self, 'bag')
        self.content = content

    def __str__(self):
        return f'{self.name}[{format_list([str(e) for e in self.content])}]'


class Bottle(Item):
    def __init__(self, fill: float):
        Item.__init__(self, 'bottle')
        self.fill = fill

    def __str__(self):
        return f'{self.name}({int(self.fill * 100)}%)'


class PoisonVial(Item):
    def __init__(self, poison: Poison):
        Item.__init__(self, poison.name + ' vial')
        self.poison = poison

    def __str__(self):
        return f'{self.name}({self.poison.name})'
