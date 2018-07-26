from thirst_games.game import Game
from thirst_games.player import Player

game = Game([
    Player('White Rabbit', 1, 'his'),
    Player('Arthour', 1, 'his'),
    Player('Sebou', 2, 'his'),
    Player('Florence', 2, 'her'),
    Player('Yah', 7, 'his'),
    Player('Bakablue', 7, 'her'),
    Player('Piou', 8, 'his'),
    Player('Meggie', 8, 'her'),
    Player('Penguin', 9, 'his'),
    Player('Wajanatrabu', 9, 'his'),
    Player('Antonin', 12, 'his'),
    Player('Tygrec', 12, 'her'),
    # Player('Powner', 100),
    # Player('The Sheep', 100),
    # Player('Foxy', 100),
    # Player('Magou', 100),
    # Player('Plukranos', 100),
    # Player('Yunne', 100),
    # Player('John', 100),
    # Player('John', 100),
    # Player('John', 100),
    # Player('John', 100),
    # Player('John', 100),
    # Player('John', 100),
])

game.run()
