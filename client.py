#import os
import socketio # pyright: ignore[reportMissingTypeStubs]
import asyncio
import curses
import curses.textpad

#from dotenv import load_dotenv

from typing import Any

SERVER = 'https://button-retrieve-breeds-reference.trycloudflare.com'
LOCAL_SERVER = 'http://127.0.0.1:8000'

sio = socketio.AsyncClient()

messages: list[dict[str,Any]] = []
grid_win: curses.window|None = None
msg_win: curses.window|None = None
input_win: curses.window|None = None

@sio.on('NOTIFY')
def handle_botify(message: dict[str,Any]):
    assert msg_win is not None

    msg_win.clear()
    msg_win.border()
    messages.append(message)

    y=1
    for msg in messages:
        msg_win.addstr(y, 1, f"{msg.get('username')}: {msg.get('message')}\n")
        y+=1

    msg_win.refresh()
    input_win.clear()
    input_win.refresh()

@sio.on('SHOW_GRID')
def handle_grid(grid):
    assert grid_win is not None

    colors = {'1': curses.COLOR_RED, '2': curses.COLOR_YELLOW}

    grid_win.clear()
    grid_win.border()

    width = len(grid[0])
    height = len(grid)

    x,y = 1,1

    grid_win.addch(y, x, '┌')
    x += 1
    for c in range(width):
        grid_win.addstr(y, x, '───')
        x += 3
        if c != (width-1):
            grid_win.addch(y, x, '┬')
            x += 1
    grid_win.addch(y, x, '┐')
    y += 1

    for r,line in enumerate(grid):
        # row
        x = 1
        grid_win.addch(y, x, '│')
        x += 1
        for i,c in enumerate(line):
            if c in {'1','2'}:
                grid_win.addstr(y, x, ' ● ', curses.color_pair(colors.get(c, 0)))
            else:
                grid_win.addstr(y, x, ' ○ ')
            x += 3
            if i != (width-1):
                grid_win.addch(y, x, '│')
                x += 1
        grid_win.addch(y, x, '│')
        y += 1

        # row separator
        if r != height-1:
            x = 1
            grid_win.addch(y, x, '├')
            x += 1
            for c in range(width):
                grid_win.addstr(y, x, '───')
                x += 3
                if c != (width-1):
                    grid_win.addch(y, x, '┼')
                    x += 1
            grid_win.addch(y, x, '┤')
            y += 1

    x = 1
    grid_win.addch(y, x, '└')
    x += 1
    for c in range(width):
        grid_win.addstr(y, x, '───')
        x += 3
        if c != (width-1):
            grid_win.addch(y, x, '┴')
            x += 1
    grid_win.addch(y, x, '┘')

    grid_win.refresh()
    input_win.clear()
    input_win.refresh()

@sio.on('ASK_COL')
async def handle_ask_col():
    assert msg_win is not None
    assert input_win is not None

    while True:
        await asyncio.sleep(0.05)
        input_win.nodelay(True)
        curses.flushinp()
        box = curses.textpad.Textbox(input_win)
        box.edit()
        message = box.gather()
        input_win.clear()
        input_win.refresh()
        return int(message)

async def main(screen: curses.window):
    global msg_win, input_win, grid_win

    screen.clear()
    screen.refresh()

    curses.init_pair(curses.COLOR_RED,
                     curses.COLOR_RED,
                     curses.COLOR_BLACK)
    curses.init_pair(curses.COLOR_YELLOW,
                     curses.COLOR_YELLOW,
                     curses.COLOR_BLACK)

    grid_win = curses.newwin(curses.LINES, curses.COLS//2, 0, 0)
    grid_win.border()
    grid_win.refresh()

    msg_win = curses.newwin(curses.LINES - 3, curses.COLS//2, 0, curses.COLS//2 + 1)
    msg_win.border()
    msg_win.refresh()

    msg_win.scrollok(True)
    input_win = curses.newwin(1, curses.COLS, curses.LINES - 2, curses.COLS//2 + 1)

    await sio.connect(
        LOCAL_SERVER,
        auth = {"username":"Test"}
    )

    await sio.wait()

#if __name__ == "__client__":
#load_dotenv()
print ("lol")
curses.wrapper(lambda screen: asyncio.run(main(screen)))