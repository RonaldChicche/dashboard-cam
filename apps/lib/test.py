from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import eventlet
import time

eventlet.monkey_patch()  # Important to make standard threads cooperate with eventlet

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

def camera_thread():
    """Function to handle camera connections and events."""
    while True:
        # Here you would add your camera connection and event handling logic
        # For demonstration, we're just printing a message every 5 seconds
        print("Camera thread is running...")
        time.sleep(5)
        # Emitting a message to all connected clients
        socketio.emit('camera_update', {'data': 'New image or camera event'})

@app.route('/')
def index():
    """Serve the index HTML file."""
    return render_template('index.html')

# Start the camera thread
threading.Thread(target=camera_thread, daemon=True).start()

if __name__ == '__main__':
    socketio.run(app)
