from typing import Union, List, Optional

from thirst_games.abstract.area import Area
from thirst_games.abstract.items import Item, Weapon


class Entity:
    def __init__(self, name: str, he: str='it'):
        self._name = name
        self.he = he
        self.him = 'him' if he == 'he' else ('her' if he == 'she' else 'it')
        self.his = 'his' if he == 'he' else ('her' if he == 'she' else 'its')
        self.status: List[str] = []
        self._current_area: Area = None
        self.destination: Area = None
        self.stealth: float = 0

    @property
    def name(self):
        return self._name

    def __str__(self):
        return self.name

    @property
    def current_area(self) -> Area:
        return self._current_area

    def move_to(self, new_area: Area):
        self._current_area = new_area

    def reveal(self):
        self.stealth = 0


class CarryingEntity(Entity):
    def loot_weapon(self, weapon: Optional[Union[Weapon, List[Weapon]]] = None):
        raise NotImplementedError

    def loot_bag(self):
        raise NotImplementedError

    def loot(self, take_a_break=True):
        raise NotImplementedError

    def craft(self):
        raise NotImplementedError

    def estimate(self, item: Union[Item, List[Item]]) -> float:
        raise NotImplementedError


class LivingEntity(Entity):
    def be_damaged(self, damage, weapon='default', attacker_name=None) -> bool:
        raise NotImplementedError

    @property
    def active_poisons(self) -> list:
        raise NotImplementedError

    def remove_poison(self, poison):
        raise NotImplementedError

    def add_poison(self, poison):
        raise NotImplementedError


class FightingEntity(LivingEntity):
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

    def enemies(self, area: Area) -> List[Entity]:
        return [p for p in area.players if p != self]  # TODO: consider

    def set_up_ambush(self):
        raise NotImplementedError

    def estimate_of_power(self, area) -> float:
        raise NotImplementedError

    def estimate_of_danger(self, area) -> float:
        raise NotImplementedError

    def can_see(self, other):
        raise NotImplementedError

    def pillage(self, stuff):
        raise NotImplementedError

    def attack_at_random(self):
        raise NotImplementedError

    def fight(self, other_player):
        raise NotImplementedError

    def go_to(self, area: Union[str, Area, Entity]) -> Optional[Area]:
        raise NotImplementedError

    def check_for_ambush_and_traps(self):
        raise NotImplementedError

    def trigger_ambush(self, prey):
        raise NotImplementedError


class AbstractTrap(Entity):
    def check(self, players, panic=False) -> bool:
        raise NotImplementedError

    def apply(self, players):
        raise NotImplementedError

    @classmethod
    def can_be_built(cls, player) -> bool:
        raise NotImplementedError
