from fastapi import FastAPI, WebSocket 
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
import json


DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

app = FastAPI()

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

Base.metadata.create_all(bind=engine)

connections = []

@app.get("/")
def home():
    return {"message" : "200! OK, Server Works Correctly"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    db = SessionLocal()
    try:
        items = db.query(CartItem).all()
        cart = [item.name for item in items]

        await websocket.send_text(json.dumps({
            "cart": cart,
            "total": len(cart),
            "message": "Connected"
        }))

        while True:
            data = await websocket.receive_text()
            data = json.loads(data)

            user = data.get("user", "Anonymous")
            message = ""

            if data["action"] == "add":
                item = CartItem(name=data["item"])
                db.add(item)
                db.commit()
                message = f"{user} added {data['item']}"

            elif data["action"] == "remove":
                item = db.query(CartItem).filter(
                    CartItem.name == data["item"]
                ).first()

                if item:
                    db.delete(item)
                    db.commit()
                    message = f"{user} removed {data['item']}"

            items = db.query(CartItem).all()
            cart = [item.name for item in items]

            for conn in connections[:]:
                try:
                    await conn.send_text(json.dumps({
                        "cart": cart,
                        "total": len(cart),
                        "message": message
                    }))
                except:
                    connections.remove(conn)

    except WebSocketDisconnect:
        print("Client disconnected")
        if websocket in connections:
            connections.remove(websocket)
