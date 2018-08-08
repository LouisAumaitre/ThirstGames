from random import random, choice
from typing import List, Dict

from thirst_games.abstract.area import Area
from thirst_games.abstract.entity import Entity, FightingEntity, CarryingEntity
from thirst_games.abstract.items import Item
from thirst_games.constants import SLEEPING, FLEEING, STARTER, TRAPPED
from thirst_games.context import Context
from thirst_games.narrator import Narrator


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


def do_a_fight(team_1: List[PlayingEntity], team_2: List[PlayingEntity]):
    initiative: Dict[PlayingEntity, float] = {}
    weapon_name: Dict[PlayingEntity, str] = {}
    print(f'FIGHT between {[p.name for p in team_1]}, {[p.name for p in team_2]}')
    drops = []
    at_area = team_1[0].current_area.at
    for e in team_1:
        initiative[e] = 1 + random()
        if not len([e2 for e2 in team_2 if e2.can_see(e)]):
            initiative[e] += 1
    for e in team_2:
        initiative[e] = 0 if SLEEPING in e.status else random()

    verbs_1 = ''
    if len([e for e in team_2 if FLEEING in e.status]) == len(team_2):
        verbs_1 = 'catches and '
    elif len([e for e in team_2 if e.stealth > 0.1]) == len(team_2):
        verbs_1 = 'finds and '

    for e in [*team_1, *team_2]:
        e.busy = True
        e.reveal()
        if FLEEING in e.status:
            e.status.remove(FLEEING)
        weapon_name[e] = f'with {e.his} {e.weapon.name}'
    fight_round = 0

    def do_attack(attacker, defender, defending_team, surprise=''):
        if attacker.hit(defender, 1 + initiative[attacker] - initiative[defender]):
            Narrator().add([
                attacker.name, verbs_1 + 'kills', defender.name, surprise, at_area, weapon_name[player_1]])
            drops.extend(player_2.drops)
            defending_team.remove(defender)
        else:
            verb = 'attacks' if fight_round == 1 else 'fights'
            Narrator().add([attacker.name, verbs_1 + verb, defender.name, at_area, weapon_name[player_1]])
            Narrator().apply_stock()
        if defender.is_alive and random() > defender.courage and defender.can_flee():
            w = defender.weapon
            defender.flee(panic=True)
            if defender.weapon != w:
                drops.append(w)
            defending_team.remove(defender)

    while len(team_1) and len(team_2) and (Context().time != STARTER or fight_round < 4):
        fight_round += 1
        for player_1 in team_1:
            if not len(team_2):
                break
            player_2 = choice(team_2)

            surprise_txt = f'in {player_2.his} sleep' if SLEEPING in player_2.status else (
                f'while {player_2.he} is trapped' if TRAPPED in player_2.status else (
                    'by surprise' if initiative[player_1] > initiative[player_2] else ''))

            do_attack(player_1, player_2, team_2, surprise_txt)
            initiative[player_1] = 1
            initiative[player_2] = 1

        for player in team_2:
            if not len(team_1):
                break
            do_attack(player, choice(team_1), team_1)
        Narrator().cut()

    if not len(team_2):
        for e in team_1:
            e.pillage(drops)
    if not len(team_1):
        for e in team_2:
            e.pillage(drops)
