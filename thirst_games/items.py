from thirst_games.narrator import format_list


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


HANDS = Weapon('bare hands', 1)


class Food(Item):
    def __init__(self, name, value):
        Item.__init__(self, name)
        self.value = value


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
