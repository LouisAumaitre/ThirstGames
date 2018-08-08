from typing import List

from thirst_games.abstract.area import Area
from thirst_games.abstract.entity import Entity, FightingEntity, CarryingEntity


class PlayingEntity(FightingEntity, CarryingEntity):
    strategy = None
    acted = False
    busy = False

    @property
    def players(self):
        return [self]

    def think(self):
        raise NotImplementedError

    def act(self):
        raise NotImplementedError

    def reset_turn(self):
        self.strategy = None
        self.acted = False

    def flee(self, panic=False, drop_verb='drops', stock=False):
        raise NotImplementedError

    def enemies(self, area: Area) -> List[Entity]:
        return [p for p in area.players if p != self]  # TODO: consider

    def loot_start(self):
        raise NotImplementedError


class Strategy:
    def __init__(self, name, pref, action):
        self.name = name
        self.pref = pref
        self.action = action

    def apply(self, player: PlayingEntity):
        out = self.action(player)
        if isinstance(out, str):
            print(f'{str(player)} {out}')


class Relationship:
    def __init__(self):
        self.friendship = 0
        self.allied = False
