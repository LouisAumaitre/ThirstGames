from typing import List, Dict

from random import choice, random

from thirst_games.abstract.playing_entity import PlayingEntity
from thirst_games.constants import STARTER, SLEEPING, TRAPPED, FLEEING
from thirst_games.context import Context
from thirst_games.narrator import Narrator


def do_a_fight(team_1: List[PlayingEntity], team_2: List[PlayingEntity]):
    initiative: Dict[PlayingEntity, float] = {}
    weapon_name: Dict[PlayingEntity, str] = {}
    drops = []
    at_area = team_1[0].current_area.at
    Narrator().new(['FIGHT between', [p.name for p in team_1], 'vs', [p.name for p in team_2], at_area])
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
        if FLEEING in e.status:
            e.status.remove(FLEEING)
        weapon_name[e] = f'with {e.his} {e.weapon.name}'
    fight_round = 0

    def do_attack(attacker, defender, defending_team, surprise=''):
        attacker.busy = True
        attacker.reveal()
        defender.busy = True
        defender.reveal()
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
    Narrator().new(['FIGHT is over', [p.name for p in team_1], 'vs', [p.name for p in team_2]])

    if not len(team_2):
        for e in team_1:
            e.pillage(drops)
    if not len(team_1):
        for e in team_2:
            e.pillage(drops)
