import os
import time
import json
import threading
from flask import request
from flask_socketio import SocketIO, emit
from .lib import XmlRpcProxyManager, PLCDataSender, ImageClient


class AlambresWebApp:
    def __init__(self):
        # Thread
        self.process = None
        # Load config
        self.config_path = os.path.join(os.path.dirname(__file__), 'lib/config.json')
        self.config = self.load_config()
        # Applications        
        self.camera_manager = XmlRpcProxyManager()
        # self.plc_client = PLCDataSender()
        self.image_manager = ImageClient()
        # timer
        self.timer = time.time()
        self.beat_time = 5

    def __del__(self):
        self.stop()

    def start_thread(self):
        self.process = threading.Thread(target=self.main)
        self.process.start()

    def stop(self):
        if self.process is not None:
            self.process.join()
            self.process = None  

    def load_config(self):
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        return config
    
    def connect_cameras(self):
        # Connect to cameras
        cam_list = [cam['ip'] for cam in self.config['cameras'] if cam['enabled']]
        try:
            cam_con = self.camera_manager.connect(cam_list)
            cam_ini = self.camera_manager.init_config()
            cam_set = self.camera_manager.set_config(0)
            # print
            for cam in range(len(cam_list)):
                if cam_con[cam][0] != 0:
                    print(f"-> Camera {cam+1} not connected")

                    continue
                print(f"-> Camera {cam+1} connected:")
                print(f"\t{cam_con[cam][1]['mac']} -> {cam_con[cam][1]['ip']}")
                # print(f"\t{cam_ini[cam][1]}")
                print(f"\tLoad config -> {cam_set[cam][0]}")
        except RuntimeError as e:
            print("Error connecting: ", e)
            return 1
        return 0
    
    def connect_plc(self):
        # Connect to plc
        plc_con = self.plc_client.connect_plc(self.config['plc']['ip'])
        if plc_con != 0:
            print("Error connecting to PLC")
            return 1
        print(f"-> PLC connected on {self.config['plc']['ip']}")
        return 0
    
    def update_plc(self):
        # Update plc data
        pass

    def check_connection(self):
        # Check Camera and PLC
        pass

    def emit_data(self, data, event):
        # Emit data to web through socketio
        if self.socketio is not None:
            self.socketio.emit(event, data)

    def main(self):
        # Connect to cameras
        self.connect_cameras()
        # connect to plc
        # self.plc_client.connect_plc()
        self.prev_state = False
        while True:
            # make a beat for cameras 
            if time.time() - self.timer > self.beat_time:
                self.timer = time.time()
                resp = self.camera_manager.heart_beat()
                print("Heart beat:", resp) 
            
    
    def web_requests(self, app, socketio):
        self.socketio = socketio

        @app.route('/connect', methods=['POST'])
        def web_connect():
            data = request.get_json()
            # print(data)

        @app.route('/disconnect', methods=['POST'])
        def web_disconnect():
            # global camera_manager
            # global plc_client
            # Connections
            print("Disconnecting devices...")

            return {'status': 'ok'}
        
        @app.route('/execute_detection', methods=['POST'])
        def web_execute_detection():
            # global camera_manager
            # global plc_client
            # Connections
            print("Executing detection...")

            return {'status': 'ok'}
        
        # Socketio events ----------------------------------------------
        @socketio.on('connect')
        def socket_connect():
            print('Client connected')
            emit('connect-response', {'response': self.config['cameras']})
        



if __name__ == "__main__":
    app = AlambresWebApp()
    app.start_thread()
    while True:
        time.sleep(10)

