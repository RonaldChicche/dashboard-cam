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
        self.plc_client = PLCDataSender()
        self.image_manager = ImageClient()
        # timer
        self.timer = time.time()
        self.beat_time = 20
        # Connection
        try:
            self.connect_cameras()
            # self.connect_plc()
        except RuntimeError as e:
            print("Error: ", e)

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
        disable_index = [i for i, cam in enumerate(self.config['cameras']) if not cam['enabled']]
        try:
            cam_con = self.camera_manager.connect(cam_list)  
            cam_ini = self.camera_manager.init_config()
            cam_set = self.camera_manager.set_config(0) 
            # add disabled cameras by their index with responses
            for i in disable_index:
                cam_con.insert(i, (1, {'mac': 'disabled', 'ip': self.config['cameras'][i]['ip']}))
                cam_set.insert(i, (0))

            # print
            for cam in range(len(cam_con)):
                # print(cam_con[cam])
                if cam_con[cam][0] != 0:
                    print(f"-> Camera {cam+1} not connected")
                    self.plc_client.cam_states[f'CAM{cam+1}_CON'] = False
                    continue
                self.plc_client.cam_states[f'CAM{cam+1}_CON'] = True
                print(f"-> Camera {cam+1} connected:")
                print(f"\t{cam_con[cam][1]['mac']} -> {cam_con[cam][1]['ip']}")
                # print(f"\t{cam_ini[cam][1]}")
                print(f"\tLoad config -> {cam_set[cam]}")
        except RuntimeError as e:
            print("Error connecting: ", e)
            return 1
        print(self.plc_client.cam_states)
        return 0
    
    def connect_plc(self):
        # Connect to plc
        plc_con = self.plc_client.connect_plc(self.config['plc']['ip'])
        if plc_con != 0:
            print("Error connecting to PLC")
            return 1
        print(f"-> PLC connected on {self.config['plc']['ip']}")
        return 0
    
    def detection_execution(self, app):
        # Execute detection
        print("Executing detection...")
        self.plc_client.cam_states['RUNNING'] = True
        self.plc_client.cam_states['READY'] = False
        # get results
        result_list = self.camera_manager.execute_detection()
        print(result_list)
        # get images
        img_list = self.camera_manager.get_images()
        # process app
        app = f"app{app:02d}"
        set_point = self.config[app]['set-point']
        differences = []
        for result in result_list:
            if result[0] == 0:
                if result[1]['y'] > set_point:
                    diff = result[1]['y'] - set_point
                elif result[1]['y'] < set_point:
                    diff = set_point - result[1]['y'] - self.config[app]['nudo']

                # pix to mm
                diff = diff * self.config['scale']['pix2mm']
                differences.append(diff)
        # print 
        
        self.plc_client.cam_states['RUNNING'] = False
        self.plc_client.cam_states['READY'] = True
        return {'results': result_list, 'differences': differences}

    def check_connection(self):
        # Check Camera and PLC
        pass

    def main(self):
        
        # self.plc_client.start_reading()
        self.prev_state = False
        while True:
            # make a beat for cameras 
            # if time.time() - self.timer > self.beat_time:
            #     self.timer = time.time()
            #     resp = self.camera_manager.heart_beat()
            #     print("Heart beat:", resp) 

            # check trigger
            if self.plc_client.plc_states["TRIG"] == False:
                self.prev_state = False

            # Excetute detection trigger
            if self.plc_client.plc_states["TRIG"] ^ self.prev_state:                
                # Execute detection
                resp = self.detection_execution(self.plc_client.plc_states["APP"]) # returns a dictionarie
                
                # Update states    
                self.prev_state = self.plc_client.plc_states["TRIG"]
                self.plc_client.cam_states['RUNNING'] = False
                

    
    def web_requests(self, app):

        @app.route('/connect', methods=['POST'])
        def web_connect():
            data = request.get_json()
            # print(data)

        @app.route('/disconnect', methods=['POST'])
        def web_disconnect():
            # Connections
            print("Disconnecting devices...")

            return {'status': 'ok'}
        
        @app.route('/execute_detection', methods=['POST'])
        def web_execute_detection():
            # Execute detection
            resp = self.detection_execution(0)
            print(f"Detection executed: {resp}")

            return {'status': 'ok'}
        
        # Socketio events ----------------------------------------------
        # @socketio.on('connect')
        # def socket_connect():
        #     print('Client connected')
        #     emit('connect-response', {'response': self.config['cameras']})
        



# if __name__ == "__main__":
#     app = AlambresWebApp()
#     app.start_thread()
#     while True:
#         time.sleep(10)

