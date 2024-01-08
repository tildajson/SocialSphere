from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

from secret import SECRET_KEY

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
socketio = SocketIO(app)


rooms = {}


def generate_unique_code(length):
    """Generate random room codes."""
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code


@app.route("/", methods=["POST", "GET"])
def home():
    """Render home page forms."""
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join-room", False)
        create = request.form.get("create-room", False)

        if not name:
            return render_template("home.html", error="Make sure to enter a name", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Enter a room code to join")

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Cannot find a room with that code", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")


@app.route("/room")
def room():
    """Render chat rooms."""
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])


@socketio.on("message")
def message(data):
    """Create and return chat messages."""
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get("name")}: {data["data"]}")


@socketio.on("connect")
def connect():
    """Connect user to chat room and generate confirmation message."""
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has joined the chat"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} has joined room {room}")


@socketio.on("disconnect")
def disconnect():
    """Disconnect user from room and generate leave message."""
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the chat"}, to=room)
    print(f"{name} has left room {room}")


if __name__ == "__main__":
    socketio.run(app, debug=True)
