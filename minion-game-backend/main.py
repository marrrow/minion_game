from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import uuid
import random

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.waiting_players: set[str] = set()
        self.game_sessions: dict[str, dict] = {}  # game_id: {player1_id, player2_id, game_state}

    async def connect(self, websocket: WebSocket, player_id: str):
        await websocket.accept()
        self.active_connections[player_id] = websocket

    def disconnect(self, player_id: str):
        if player_id in self.active_connections:
            del self.active_connections[player_id]
        if player_id in self.waiting_players:
            self.waiting_players.remove(player_id)

    async def find_match(self, player_id: str):
        self.waiting_players.add(player_id)
        if len(self.waiting_players) >= 2:
            player1_id = self.waiting_players.pop()
            player2_id = self.waiting_players.pop()
            game_id = str(uuid.uuid4())
            self.game_sessions[game_id] = {
                "players": [player1_id, player2_id],
                "game_state": {
                    "scores": {player1_id: 0, player2_id: 0},
                    "lives": {player1_id: 3, player2_id: 3},
                    "items": [],
                    "chaos_mode": False,
                    "chaos_timer": 0
                }
            }
            # Notify both players
            await self.active_connections[player1_id].send_json({
                "type": "GAME_START",
                "game_id": game_id,
                "opponent_id": player2_id
            })
            await self.active_connections[player2_id].send_json({
                "type": "GAME_START",
                "game_id": game_id,
                "opponent_id": player1_id
            })
            # Start game loop
            asyncio.create_task(self.game_loop(game_id))

    async def game_loop(self, game_id: str):
        while game_id in self.game_sessions:
            game_state = self.game_sessions[game_id]["game_state"]
            # Generate items
            if random.random() < 0.02 * (3 if game_state["chaos_mode"] else 1):
                item = {
                    "id": str(uuid.uuid4()),
                    "x": random.random() * 280,
                    "y": 0,
                    "type": "egg" if random.random() > 0.3 else "rotten_egg"
                }
                game_state["items"].append(item)
                await self.broadcast_to_game(game_id, {
                    "type": "ITEM_SPAWN",
                    "item": item
                })
            # Move items
            for item in game_state["items"]:
                item["y"] += 2 * (3 if game_state["chaos_mode"] else 1)
            # Check for chaos mode
            game_state["chaos_timer"] += 1
            if game_state["chaos_timer"] >= 200:  # 20 seconds
                game_state["chaos_mode"] = True
                await self.broadcast_to_game(game_id, {
                    "type": "CHAOS_MODE",
                    "active": True
                })
            if game_state["chaos_timer"] >= 250:  # 25 seconds
                game_state["chaos_mode"] = False
                game_state["chaos_timer"] = 0
                await self.broadcast_to_game(game_id, {
                    "type": "CHAOS_MODE",
                    "active": False
                })
            # Broadcast game state
            await self.broadcast_to_game(game_id, {
                "type": "GAME_STATE",
                "items": game_state["items"]
            })
            await asyncio.sleep(0.05)

    async def broadcast_to_game(self, game_id: str, message: dict):
        if game_id in self.game_sessions:
            for player_id in self.game_sessions[game_id]["players"]:
                await self.active_connections[player_id].send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    await manager.connect(websocket, player_id)
    try:
        await manager.find_match(player_id)
        while True:
            data = await websocket.receive_json()
            if data["type"] == "PLAYER_MOVE":
                await manager.broadcast_to_game(data["game_id"], {
                    "type": "OPPONENT_MOVE",
                    "position": data["position"]
                })
            elif data["type"] == "ITEM_COLLECTED":
                game_id = data["game_id"]
                player_id = data["player_id"]
                item_id = data["item_id"]
                game_state = manager.game_sessions[game_id]["game_state"]
                item = next((item for item in game_state["items"] if item["id"] == item_id), None)
                if item:
                    if item["type"] == "egg":
                        game_state["scores"][player_id] += 10
                    else:
                        game_state["lives"][player_id] -= 1
                        if game_state["lives"][player_id] <= 0:
                            await manager.broadcast_to_game(game_id, {
                                "type": "GAME_OVER",
                                "winner": [p for p in game_state["players"] if p != player_id][0]
                            })
                            del manager.game_sessions[game_id]
                    game_state["items"] = [item for item in game_state["items"] if item["id"] != item_id]
                    await manager.broadcast_to_game(game_id, {
                        "type": "GAME_STATE",
                        "scores": game_state["scores"],
                        "lives": game_state["lives"],
                        "items": game_state["items"]
                    })
    except WebSocketDisconnect:
        manager.disconnect(player_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
