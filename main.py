import socketio
import uvicorn
import asyncio
from power_four import PowerFour

sio = socketio.AsyncServer(async_mode='asgi') #ASG = asynchronous getway app
app = socketio.ASGIApp(sio)
clients={}#sid,name,idroom
id_room =0
rooms={0:0}

@sio.event
async def connect(sid, environement, auth):
    global id_room
    if rooms[id_room]==2:
        id_room+=1
    clients[sid]={"user":auth.get('username'),"idroom":id_room}
    rooms.setdefault(id_room,0)
    rooms[id_room]+=1
    await sio.enter_room(sid, id_room)
    print(f'{auth.get('username')} c\'est connecté à la room{id_room}')

@sio.event
async def disconnect(sid):
    await sio.leave_room(sid, clients[sid]["id_room"])
    print(f"{clients.get(sid)} c'est deconnecté de la room {clients[sid]["id_room"]}")
    clients.pop(sid)

@sio.on('PLAY')
async def play(player,col):
    #if grid.add_chip(player,col):
        #check if won
        #pass play to other player
        pass




if __name__ == '__main__':
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)