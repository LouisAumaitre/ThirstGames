from thirst_games.constants import NARRATOR


class Poison:
    def __init__(self, name, amount, damage):
        self.name = name
        self.amount = amount
        self.damage = damage

    def upkeep(self, player, **context):
        if self.amount == 0:
            player.remove_poison(self, **context)
            return
        self.amount -= 1
        if player.add_health(-self.damage, **context):
            context[NARRATOR].new([player.first_name, 'succumbs', 'to the', self.name])

    def __str__(self):
        return f'{self.name}({int(self.damage * 100)}x{self.amount})'
