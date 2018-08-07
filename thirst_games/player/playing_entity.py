from typing import List

from thirst_games.map import Area, Positionable
from thirst_games.player.carrier import CarryingEntity
from thirst_games.player.fighter import FightingEntity


class PlayingEntity(FightingEntity, CarryingEntity):
    strategy = None
    acted = False

    @property
    def name(self) -> str:
        raise NotImplementedError

    def think(self):
        raise NotImplementedError

    def act(self):
        raise NotImplementedError

    def reset_turn(self):
        self.strategy = None
        self.acted = False

    @property
    def is_alive(self):
        raise NotImplementedError

    @property
    def courage(self) -> float:
        raise NotImplementedError

    @property
    def dangerosity(self) -> float:
        raise NotImplementedError

    def flee(self, panic=False, drop_verb='drops', stock=False):
        raise NotImplementedError

    def pursue(self):
        raise NotImplementedError

    def enemies(self, area: Area) -> List[Positionable]:
        return [p for p in area.players if p != self]  # TODO: consider

    def set_up_ambush(self):
        raise NotImplementedError

    def estimate_of_power(self, area) -> float:
        raise NotImplementedError

    def estimate_of_danger(self, area) -> float:
        raise NotImplementedError

    def can_see(self, other: Positionable):
        raise NotImplementedError

    def pillage(self, stuff):
        raise NotImplementedError

    def attack_at_random(self):
        raise NotImplementedError

    def fight(self, other_player):
        raise NotImplementedError

    def hide(self):
        raise NotImplementedError

    def loot_weapon(self, weapon=None):
        raise NotImplementedError

    def loot_bag(self):
        raise NotImplementedError

    def loot(self, take_a_break=True):
        raise NotImplementedError

    def craft(self):
        raise NotImplementedError

    def go_get_drop(self):
        raise NotImplementedError

    def go_to(self, area):
        raise NotImplementedError

    def check_for_ambush_and_traps(self):
        raise NotImplementedError

    def estimate(self, item) -> float:
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