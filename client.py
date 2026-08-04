import os
import socketio # pyright: ignore[reportMissingTypeStubs]
import asyncio
import curses
import curses.ascii
import curses.textpad
import threading
from collections import deque

from dotenv import load_dotenv

from typing import Any

sio: socketio.AsyncClient = socketio.AsyncClient()

messages: deque[dict[str,str]]|None = None

# Curses windows
grid_win: curses.window|None = None
msg_win: curses.window|None = None
input_win: curses.window|None = None

# Lock and Threads
input_lock: asyncio.Lock = asyncio.Lock()
stop_event = asyncio.Event()
interrupt_flag = threading.Event()

username: str|None = None
input_listener: asyncio.Task[Any]|None = None
should_reconnect: bool = False

# Custom Exception to raise and handle when a client requires to quit
class UserQuit(Exception):
    pass

# Check n is a valid integer
def is_integer(n: str):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()

# custom validator for cureses textpad textbox: allow to force return an empty value and free the lock
def edit_validator(ch: str|int) -> str|int:
    if interrupt_flag.is_set():
        return curses.ascii.BEL
    if ch == -1:    # timeout, personne n'a tapé
        return 0    # "if not ch: continue" dans edit() -> on reboucle proprement
    return ch

# Utility: display the stored messages and refresh the msg window
def refresh_message_window() -> None:
    assert messages is not None
    assert msg_win is not None
    assert input_win is not None
    colors: dict[str,int] = {'system':curses.COLOR_YELLOW, 'client':curses.COLOR_CYAN}

    msg_win.clear()
    msg_win.border()
    y=1

    for msg in messages:
        user: str = msg.get('username','undefined')
        msg_win.addstr(y, 1, f"{user}: {msg.get('message')}\n", curses.color_pair(colors.get(user, 0)))
        y+=1
    
    msg_win.refresh()

    # focus back on the input window
    input_win.clear()
    input_win.refresh()

@sio.on('NOTIFY')
def handle_notify(message: dict[str,Any]|None = None):
    """ if a message is passed add it the queue. Refresh the msg window regardless """
    assert messages is not None

    if message is not None:
        messages.append(message)

    refresh_message_window()

@sio.on('SHOW_GRID')
def handle_grid(grid: list[list[str]]):
    """ Display the current game in a grid """
    assert grid_win is not None
    assert input_win is not None

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

    # focus back on the input window
    input_win.clear()
    input_win.refresh()

# Utility: listen to the input and return the value. if quit is entered, prepare and announce shutdown then raise the custom exception UserQuit 
async def _read_input() -> str:
    assert messages is not None
    assert input_win is not None
    input_win.clear()
    input_win.refresh()

    loop = asyncio.get_event_loop()
    curses.flushinp()
    box = curses.textpad.Textbox(input_win)
    box.win.timeout(100)
    input = await loop.run_in_executor(None, box.edit, edit_validator)

    if input.strip() == 'quit':
        messages.append({"username":"client","message":"User asked to disconnect"})
        messages.append({"username":"client","message":"Shutting down ..."})
        refresh_message_window()
        await asyncio.sleep(1)
        await sio.disconnect()
        raise UserQuit()
    
    return input.strip()

@sio.on('ASK_COL')
async def handle_ask_col() -> int:
    """ Trigger by the server. Ask for the column to play. Alway return an integer"""
    interrupt_flag.set()

    while True:
        async with input_lock:
            await asyncio.sleep(0.05)
            interrupt_flag.clear()
            input = await _read_input()

            if is_integer(input):
                continue

            return int(input)

# Simply listen for the response to whether to client wants to quit or try to reconnect after a forced disconection from the server
async def handle_ask_reconnect():
    interrupt_flag.set()

    async with input_lock:
        await asyncio.sleep(0.05)
        interrupt_flag.clear()
        input = await _read_input()
        return input in ('y','Y','yes','Yes')

# When the client is connected and no other listener is on the input, listen to the input and send value as message to the server
async def listen_input():
    """ Handle textbx input when the player is waiting for his turn """
    while True:
        if not input_lock.locked():
            async with input_lock:
                await asyncio.sleep(0.05)
                input = await _read_input()

                if interrupt_flag.is_set():
                    interrupt_flag.clear()
                    continue

                if len(input) == 0:
                    continue

                await sio.emit('NEW_MESSAGE', input)
        else:
            await asyncio.sleep(0.05)

# Ask for the client username to use during the connection
async def get_username():
    assert messages is not None

    messages.append({"username":"client","message":"enter a user"})
    refresh_message_window()

    while True:
        await asyncio.sleep(0.05)
        input = await _read_input()

        if len(input) == 0:
            continue

        messages.append({"username":"client","message":f"user choose:{input}"})
        refresh_message_window()
        return input

@sio.event
async def disconnect(reason: str):
    """ Disconnection event handler. If the user was forced to disconnect, ask what to do, otherwise keep interrupting processus """
    global should_reconnect
    assert messages is not None
    assert msg_win is not None
    assert input_win is not None
    assert grid_win is not None
    interrupt_flag.set()

    if reason != sio.reason.CLIENT_DISCONNECT:
        messages.clear()

        msg_win.clear()
        msg_win.refresh()

        input_win.clear()
        input_win.refresh()

        grid_win.clear()
        grid_win.refresh()

        handle_notify({'username':'client','message':'Disconnected from the server'})
        handle_notify({'username':'client','message':'Do you want to try to reconnect ? (y|n)'})
        should_reconnect = await handle_ask_reconnect()
    else:
        should_reconnect = False

    stop_event.set()

async def main(screen: curses.window):
    global msg_win, input_win, grid_win, messages, username, input_listener

    screen.clear()
    screen.refresh()

    curses.init_pair(curses.COLOR_CYAN,
                     curses.COLOR_CYAN,
                     curses.COLOR_BLACK)
    curses.init_pair(curses.COLOR_RED,
                     curses.COLOR_RED,
                     curses.COLOR_BLACK)
    curses.init_pair(curses.COLOR_YELLOW,
                     curses.COLOR_YELLOW,
                     curses.COLOR_BLACK)

    # Grid window to display the game grid
    grid_win = curses.newwin(curses.LINES, curses.COLS//2, 0, 0)
    grid_win.border()
    grid_win.refresh()

    # Message window and messages queue to handle messages
    msg_win = curses.newwin(curses.LINES - 3, curses.COLS//2, 0, curses.COLS//2 + 1)
    messages = deque([], maxlen=msg_win.getmaxyx()[0] - 2)
    msg_win.border()
    msg_win.refresh()

    # Info window, simple text message to inform the client how to quit
    info_win = curses.newwin(1, curses.COLS//2, curses.LINES - 3, curses.COLS//2 + 1)
    info_win.addstr(0, 0, "quit = Disconnect and close the client", curses.color_pair(curses.COLOR_YELLOW))
    info_win.refresh()

    # Input window, used to handle interactive input
    input_win = curses.newwin(1, curses.COLS//2, curses.LINES - 2, curses.COLS//2 + 1)

    username = None

    while True:
        stop_event.clear()

        if username is None:
            try:
                username = await get_username()
            except UserQuit:
                break

        await sio.connect(
            os.getenv('HOST'),
            auth = {"username": username}
        )

        input_listener = asyncio.create_task(listen_input())

        await stop_event.wait()

        input_listener.cancel()
        try:
            await input_listener
        except asyncio.CancelledError:
            pass

        # Confirm that the client was disconnected, otherwise force closure
        if sio.eio.http is not None and not sio.eio.http.closed:
            await sio.eio.http.close()
        await asyncio.sleep(0.25)

        # If the user asked for reconnection, cler the messages queue, else end processus
        if not should_reconnect:
            break
        else:
            messages.clear()

load_dotenv()
curses.wrapper(lambda screen: asyncio.run(main(screen)))