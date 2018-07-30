from typing import Type

from random import random

from thirst_games.constants import NARRATOR, PANIC, MAP


class Trap:
    ingredients = []
    areas = []
    requires_tools = False
    name = 'trap'

    def __init__(self, owner, stealth):
        self.long_name = f'{owner.first_name}\'s {self.name}'
        self.owner = owner
        self.knowing = [owner]
        self.stealth = stealth

    def check(self, player, **context) -> bool:
        if context[PANIC]:
            return random() > 0.5
        if player in self.knowing:
            return False
        if random() * player.wisdom > self.stealth:
            context[NARRATOR].add([player.first_name, 'notices', self.long_name])
            self.knowing.append(player)
        return random() > 0.5

    def _apply(self, name, player, **context):
        raise NotImplementedError

    def apply(self, player, **context):
        name = self.long_name
        if player is self.owner:
            name = f'{player.his} own {self.name}'
        self._apply(name, player, **context)

    @classmethod
    def can_be_built(cls, player, **context) -> bool:
        if cls.requires_tools and not player.has_crafting_tool:
            return False
        player_stuff = [i.name for i in player.equipment]
        for item in cls.ingredients:
            if item not in player_stuff:
                return False
        if cls.areas != [] and player.current_area not in cls.areas:
            return False
        return True


def build_trap(player, trap_class: Type[Trap], **context):
    player.reveal()
    if not trap_class.can_be_built(player, **context):
        return
    trap = trap_class(player, random() / 2 + 0.5)
    context[MAP].traps[player.current_area].append(trap)
    context[MAP].test = True
    context[NARRATOR].add([player.first_name, 'builds', 'a', trap.name, f'at {player.current_area}'])


def can_build_any_trap(player, **context) -> bool:
    for trap_class in [StakeTrap]:
        if trap_class.can_be_built(player, **context):
            return True
    return False


def build_any_trap(player, **context):
    for trap_class in [StakeTrap]:
        if trap_class.can_be_built(player, **context):
            return build_trap(player, trap_class, **context)


class StakeTrap(Trap):
    ingredients = ['rope']
    areas = ['forest', 'jungle']
    requires_tools = True
    name = 'stake trap'

    def _apply(self, name, player, **context):
        if player.be_damaged(random(), 'trident', **context):
            context[NARRATOR].add([player.first_name, 'impales', f'{player.him}self', 'on', name])
        else:
            context[NARRATOR].add([player.first_name, 'falls', f'into', name])
            context[NARRATOR].apply_stock()
