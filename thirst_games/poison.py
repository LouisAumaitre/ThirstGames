from thirst_games.constants import NARRATOR, MAP, DAY


class Poison:
    def __init__(self, name, amount, damage):
        self.name = name
        self.long_name = 'the ' + name
        self.amount = amount
        self.damage = damage

    def upkeep(self, player, **context):
        if self.amount == 0:
            player.remove_poison(self, **context)
            return
        self.amount -= 1
        live = player.is_alive
        player.add_health(-self.damage, **context)
        if live and not player.is_alive:
            context[NARRATOR].new([player.first_name, 'succumbs', 'to', self.long_name])

    def __str__(self):
        return f'{self.name}({int(self.damage * 100)}x{self.amount})'
