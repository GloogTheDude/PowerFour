#import os
import socketio # pyright: ignore[reportMissingTypeStubs]
import asyncio
import curses
import curses.textpad

#from dotenv import load_dotenv

from typing import Any

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
    messages.append(message)

    for msg in messages:
        msg_win.addstr(f"{msg.get('username')}: {msg.get('message')}\n")
    msg_win.refresh()

@sio.on('SHOW_GRID')
def handle_grid(grid):
    assert grid_win is not None

    grid_win.clear()
    for line in grid:
        grid_win.addstr(f"{line}\n")
    grid_win.refresh()

@sio.on('ASK_COL')
async def handle_ask_col():
    assert msg_win is not None
    assert input_win is not None

    while True:
        await asyncio.sleep(0.05)
        input_win.nodelay(True)

        box = curses.textpad.Textbox(input_win)
        box.edit()
        message = box.gather()
        input_win.clear()
        input_win.refresh()
        return message

async def main(screen: curses.window):
    global msg_win, input_win, grid_win

    screen.clear()
    screen.refresh()

    grid_win = curses.newwin(curses.LINES, curses.COLS//2, 0, 0)
    msg_win = curses.newwin(curses.LINES - 3, curses.COLS//2, 0, curses.COLS//2 + 1)
    msg_win.scrollok(True)
    input_win = curses.newwin(1, curses.COLS, curses.LINES - 2, curses.COLS//2 + 1)

    await sio.connect(
        'http://127.0.0.1:8000',
        'user'
    )

    await sio.wait()

if __name__ == "__client__":
    #load_dotenv()

    curses.wrapper(lambda screen: asyncio.run(main(screen)))