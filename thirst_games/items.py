class Item:
    def __init__(self, name):
        self.name = name


class Weapon(Item):
    def __init__(self, name, damage_mult):
        Item.__init__(self, name)
        self.damage_mult = damage_mult


HANDS = Weapon('bare hands', 1)
