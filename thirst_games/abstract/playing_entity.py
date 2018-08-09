from random import random
from typing import List

from thirst_games.abstract.area import Area
from thirst_games.abstract.entity import Entity, FightingEntity, CarryingEntity
from thirst_games.narrator import Narrator


class PlayingEntity(FightingEntity, CarryingEntity):
    strategy = None
    acted = False
    busy = False

    @property
    def players(self):
        return [self]

    def current_group(self):
        raise NotImplementedError

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

    def relationship(self, other_player) -> Relationship:
        raise NotImplementedError

    def should_ask_to_ally(self, player) -> float:
        want = self.want_to_ally(player)
        reply_likeliness = player.relationship(self).friendship * self.dangerosity
        return want * reply_likeliness

    def ask_to_ally(self, player):
        if random() < player.want_to_ally(self):
            Narrator().new([self.name, 'proposes', 'an alliance to', player.name, 'and', player.he, 'accepts!'])
            self.new_ally(player)
            player.new_ally(self)
        else:
            Narrator().new([self.name, 'proposes', 'an alliance to', player.name, 'but', player.he, 'refuses'])
            self.relationship(player).add_friendship(-0.5)

    def want_to_ally(self, player) -> float:
        raise NotImplementedError

    def new_ally(self, player):
        self.relationship(player).set_allied(True)


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
        self._friendship = 0
        self._trust = 0
        self._allied = False

    @property
    def friendship(self):
        return self._friendship

    def add_friendship(self, value: float):
        self._friendship = max(-1, min(1, self._friendship + value))

    @property
    def trust(self):
        return self._trust

    def add_trust(self, value: float):
        self._trust = max(-1, min(1, self._trust + value))

    @property
    def allied(self) -> bool:
        return self._allied

    def set_allied(self, value: bool):
        self._allied = value


class GroupedRelationship(Relationship):
    def __init__(self, relations: List[Relationship]):
        Relationship.__init__(self)
        self.sub_relations = relations

    @property
    def friendship(self):
        return sum([r.friendship for r in self.sub_relations]) / len(self.sub_relations)

    def add_friendship(self, value: float):
        for r in self.sub_relations:
            r.add_friendship(value)

    @property
    def trust(self):
        return sum([r.trust for r in self.sub_relations]) / len(self.sub_relations)

    def add_trust(self, value: float):
        for r in self.sub_relations:
            r.add_trust(value)

    @property
    def allied(self) -> bool:
        return sum([r.allied for r in self.sub_relations]) == len(self.sub_relations)

    def set_allied(self, value: bool):
        for r in self.sub_relations:
            r.set_allied(value)

