class Item:
    def __init__(self, name):
        self.name = name
        self.long_name = 'a ' + name if name[0] not in ['a', 'e', 'i', 'o', 'u'] else 'an ' + name
        if name[-1] == 's':
            self.long_name = name


class Weapon(Item):
    def __init__(self, name, damage_mult):
        Item.__init__(self, name)
        self.damage_mult = damage_mult


HANDS = Weapon('bare hands', 1)


class Food(Item):
    def __init__(self, name, value):
        Item.__init__(self, name)
        self.value = value
