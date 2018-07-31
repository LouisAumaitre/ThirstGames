from thirst_games.game import Game
from thirst_games.player.player import Player

game = Game([
    # Player('Tutur', 1, 'his'),
    # Player('Angie', 1, 'her'),
    # Player('Sebou', 2, 'his'),
    # Player('Florence', 2, 'her'),
    Player('Rabbit', 3, 'his'),
    Player('Magou', 3, 'her'),
    Player('Powner', 4, 'his'),
    Player('Yunne', 4, 'his'),
    Player('The Sheep', 5, 'his'),
    # Player('Claire', 5, 'her'),
    # Player('Pierre', 6, 'his'),
    Player('Foxy', 6, 'her'),
    Player('Yah', 7, 'his'),
    Player('Bakablue', 7, 'her'),
    Player('Piou', 8, 'his'),
    Player('Meggie', 8, 'her'),
    Player('Penguin', 9, 'his'),
    Player('Wajanatrabu', 9, 'his'),
    # Player('Nathan', 10, 'his'),
    # Player('Delphine', 10, 'her'),
    # Player('Romain', 11, 'his'),
    # Player('Polukranos', 11, 'his'),
    Player('Antonin', 12, 'his'),
    Player('Tygrec', 12, 'her'),
])

game.run()
print(game.map.test)
