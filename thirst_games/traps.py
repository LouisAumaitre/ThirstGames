from typing import Type, List, Union

from random import random, choice

from thirst_games.constants import TRAPPED
from thirst_games.map import START_AREA, Positionable, Map
from thirst_games.narrator import Narrator
from thirst_games.player.playing_entity import PlayingEntity


class Trap(Positionable):
    ingredients = []
    areas = []
    requires_tools = False
    name = 'trap'
    group_trap = False

    def __init__(self, owner, stealth):
        self.long_name = f'{owner.first_name}\'s {self.name}'
        self.owner = owner
        self.knowing = [owner]
        self.stealth = stealth
        Map().add_trap(self, owner)

    def check(self, players: Union[PlayingEntity, List[PlayingEntity]], panic=False) -> bool:
        if not isinstance(players, list):
            players = [players]
        if panic:
            return random() > 0.5
        noticed = False
        for player in players:
            if player in self.knowing:
                noticed = True
                break
            if player.can_see(self):
                Narrator().add([player.name, 'notices', self.long_name])
                noticed = True
                break
        if noticed:
            for player in players:
                if player not in self.knowing:
                    self.knowing.append(player)
            return False
        return random() > 0.5

    def _apply(self, name, player):
        raise NotImplementedError

    def apply(self, players: Union[PlayingEntity, List[PlayingEntity]]):
        if not isinstance(players, list):
            players = [players]
        if not self.group_trap:
            players = [choice(players)]
        for player in players:
            name = self.long_name
            if player is self.owner:
                name = f'{player.his} own {self.name}'
            self.map.remove_trap(self)
            player.reveal()
            self._apply(name, player)

    @classmethod
    def can_be_built(cls, player) -> bool:
        if cls.requires_tools and not player.has_crafting_tool:
            return False
        for item in cls.ingredients:
            if not player.has_item(item):
                return False
        if cls.areas != [] and player.current_area not in cls.areas:
            return False
        return True


class StakeTrap(Trap):
    ingredients = ['rope']
    areas = ['the forest', 'the jungle']
    requires_tools = True
    name = 'stake trap'

    def _apply(self, name, player):
        if player.be_damaged(random(), 'trident'):
            Narrator().new([player.first_name, 'impales', f'{player.him}self', 'on', f'{name}!'])
        else:
            Narrator().new([player.first_name, 'falls', f'into', f'{name}!'])
            if not Narrator().has_stock:
                Narrator().add([player.first_name, 'is', 'lightly wounded'])
            Narrator().apply_stock()


class ExplosiveTrap(Trap):
    ingredients = ['explosive']
    areas = []
    requires_tools = False
    name = 'explosive trap'
    group_trap = True

    def _apply(self, name, player):
        if player.be_damaged(random() * 5, 'fire'):
            Narrator().new([player.first_name, 'blows up', 'on', f'{name}!'])
        else:
            Narrator().new([player.first_name, 'steps', 'on', f'{name}!'])
            if not Narrator().has_stock:
                Narrator().add([player.first_name, 'is', 'wounded'])
            Narrator().apply_stock()


class NetTrap(Trap):
    ingredients = ['net', 'rope']
    areas = ['the forest', 'the jungle', 'the ruins', START_AREA]
    requires_tools = False
    name = 'net trap'

    def _apply(self, name, player):
        Narrator().new([player.first_name, 'gets', 'ensnared into', f'{name}!'])
        player.status.append(TRAPPED)
        take_advantage_of_trap(self, player)


class WireTrap(Trap):
    ingredients = ['wire']
    areas = ['the forest', 'the jungle', 'the ruins', START_AREA, 'the river']
    requires_tools = False
    name = 'wire trap'

    def _apply(self, name, player):
        Narrator().new([player.first_name, 'gets', 'ensnared into', f'{name}!'])
        if random() > 0.5:
            player.status.append('leg wound')
            Narrator().add([player.first_name, 'wounds', player.his, 'leg'])
        else:
            player.status.append(TRAPPED)
            take_advantage_of_trap(self, player)


def take_advantage_of_trap(trap, player):
    if trap.owner.current_area == player.current_area and not trap.owner.busy:
        # can attack
        if trap.owner.dangerosity() > player.dangerosity():
            Narrator().cut()
            trap.owner.fight(player)


def build_trap(player, trap_class: Type[Trap]):
    player.reveal()
    if not trap_class.can_be_built(player):
        return
    for ingredient in trap_class.ingredients:
        item = [i for i in player.equipment if i.name == ingredient][0]
        player.remove_item(item)
    trap = trap_class(player, random() / 2 + 0.5)
    Narrator().add([player.first_name, 'builds', 'a', trap.name, f'at {player.current_area}'])


def can_build_any_trap(player) -> bool:
    for trap_class in [StakeTrap, ExplosiveTrap, NetTrap]:
        if trap_class.can_be_built(player):
            return True
    return False


def build_any_trap(player):
    for trap_class in [StakeTrap, ExplosiveTrap, NetTrap]:
        if trap_class.can_be_built(player):
            return build_trap(player, trap_class)
