from typing import List

from thirst_games.abstract.area import Area
from thirst_games.abstract.entity import Entity, FightingEntity, CarryingEntity


class PlayingEntity(FightingEntity, CarryingEntity):
    strategy = None
    acted = False
    busy = False

    def think(self):
        raise NotImplementedError

    def act(self):
        raise NotImplementedError

    def reset_turn(self):
        self.strategy = None
        self.acted = False

    def flee(self, panic=False, drop_verb='drops', stock=False):
        raise NotImplementedError

    def pursue(self):
        raise NotImplementedError

    def enemies(self, area: Area) -> List[Entity]:
        return [p for p in area.players if p != self]  # TODO: consider

    def set_up_ambush(self):
        raise NotImplementedError

    def estimate_of_power(self, area) -> float:
        raise NotImplementedError

    def estimate_of_danger(self, area) -> float:
        raise NotImplementedError

    def can_see(self, other: Entity):
        raise NotImplementedError

    def pillage(self, stuff):
        raise NotImplementedError

    def attack_at_random(self):
        raise NotImplementedError

    def fight(self, other_player):
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
