import logging

from const import WIDTH,HEIGHT,EMPTY_SYMB

#logging.basicConfig(
#    filename="server.log",
#    format="{asctime} - {levelname} - {message}",
#    style="{",
#    datefmt="%Y-%m-%d %H:%M",
#)
logger = logging.getLogger()

class PowerFour():
    grid: list[list[str]]
    last_chip_played: tuple[int,int]

    def __init__(self) -> None:
        self.grid = [[EMPTY_SYMB for _ in range(WIDTH)]for _ in range(HEIGHT)] 
        self.last_chip_played = (-1,-1)

    def get_formated_last_chip(self) -> tuple[int,int]:
        x = self.last_chip_played[1]+1
        y = 6 - (self.last_chip_played[0])
        return (x,y)
    
    def add_chip(self, no_player:int, col:int) -> bool:
        #print(bool(0<= int(col) < WIDTH))
        #print(f"add chip({no_player}, {col})")
        logger.info(f"try to add chip({no_player}, {col})")

        if bool(0<= int(col) <WIDTH):
            for j in range(HEIGHT-1, -1,-1):
                #print(f"j={j}")
                if self.grid[j][col] == EMPTY_SYMB:
                    self.grid[j][col] = str(no_player)
                    self.last_chip_played = (j,col)
                    #print("valid")
                    logger.info(f"chip({no_player} added to {col})")
                    return True

        logger.info(f'Invalid column received {col}')
        #print('invalid')
        return False

    def is_won(self) -> bool:
        start_r, start_c = self.last_chip_played
        player = self.grid[start_r][start_c]

        axes = [
            ((0, -1), (0, 1)),    # horizontal
            ((-1, 0), (1, 0)),    # vertical
            ((-1, -1), (1, 1)),   # diagonale \
            ((-1, 1), (1, -1)),   # diagonale /
        ]

        for direction_1, direction_2 in axes:
            count = 1  # Le dernier jeton joué

            for dr, dc in (direction_1, direction_2):
                r = start_r + dr
                c = start_c + dc

                while (
                    0 <= r < HEIGHT
                    and 0 <= c < WIDTH
                    and self.grid[r][c] == player
                ):
                    count += 1
                    r += dr
                    c += dc

            if count >= 4:
                return True

        return False