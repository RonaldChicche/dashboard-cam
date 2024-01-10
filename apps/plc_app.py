import os
import time
import json
import threading
import base64
from flask import request
from flask_socketio import SocketIO, emit
from .lib import XmlRpcProxyManager, PLCDataSender, ImageClient


class AlambresWebApp:
    def __init__(self):
        # Thread
        self.process = None
        self.run = True
        # Load config
        self.config_path = os.path.join(os.path.dirname(__file__), 'lib/config.json')
        self.config = self.load_config()
        # Applications        
        self.camera_manager = XmlRpcProxyManager()
        self.plc_client = PLCDataSender()
        self.image_manager = ImageClient()
        # Timer
        self.timer = time.time()
        self.beat_time = 50
        # Connection
        try:
            self.connect_cameras()
            self.connect_plc()
        except RuntimeError as e:
            print("Error: ", e)

    def __del__(self):
        self.stop()

    def start_thread(self):
        self.process = threading.Thread(target=self.main, daemon=True)
        self.process.start()

    def stop(self):
        if self.process is not None:
            self.run = False
            self.process.join()
            self.process = None  
        if self.camera_manager is not None:
            self.camera_manager.disconnect()
            self.camera_manager = None
        if self.plc_client is not None:
            self.plc_client.stop_reading()
            self.plc_client.disconnect_plc()
            self.plc_client = None
        print("Devices disconnected")

    def load_config(self):
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        return config
    
    def connect_cameras(self):
        # Connect to cameras
        cam_list = [cam['ip'] for cam in self.config['cameras']]
        enable_index = [i for i, cam in enumerate(self.config['cameras']) if cam['enabled']]
        try:
            cam_con = self.camera_manager.connect(cam_list, enable_index)
            # add disabled cameras by their index with responses
            # for i in range(len(cam_list)):
            #     if i not in enable_index:
            #         cam_con.insert(i, (1, {'mac': 'disabled', 'ip': self.config['cameras'][i]['ip']}))
                # cam_set.insert(i, (0))
            # print
            for cam in range(len(cam_con)):
                if cam_con[cam] is None:
                    print(f"-> Camera {cam+1} not connected")
                    self.plc_client.cam_states[f'CAM{cam+1}_CON'] = False
                    continue
                # print(cam_con[cam])
                if cam_con[cam][0] != 0:
                    print(f"-> Camera {cam+1} not connected")
                    self.plc_client.cam_states[f'CAM{cam+1}_CON'] = False
                    continue
                self.plc_client.cam_states[f'CAM{cam+1}_CON'] = True
                print(f"-> Camera {cam+1} connected:")
                print(f"\t{cam_con[cam][2]['mac']} -> {cam_con[cam][2]['ip']}")
                # print(f"\t{cam_ini[cam][1]}")
                print(f"\tLoad config -> {cam_con[cam][1]}")
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
    
    def method_test(self, app):
        # Process app
        app = f"app{app:02d}"

        # get index from the "names" area inside "cameras": "cam02" -> 2, make a list with that if they are enamled
        cam_list = [int(cam["name"][3:]) for cam in self.config[app]['cameras'] if self.config['cameras'][int(cam["name"][3:])]['enabled'] ]
        
        cameras = self.config[app]['cameras']
        # Process indexes and differences
        for index in cam_list:
            name = f"cam{index:02d}"
            # get the camera dictionarie from the selected app by name
            cam = [cam for cam in cameras if cam['name'] == name][0]

            # Verify plc cut order
            if self.plc_client.plc_states['TRIG_CUT'] == True:
                set_point = cam['set-merma']
            else:
                set_point = cam['set-point']
            print("set_point:", set_point)

        
        print(cam_list)

    def eliminar_outliers(self, lista, num_desviaciones=2):
        media = sum(lista) / len(lista)
        desviacion_estandar = (sum((x - media) ** 2 for x in lista) / len(lista)) ** 0.5
        return [x for x in lista if abs(x - media) <= num_desviaciones * desviacion_estandar]

    
    def detection_execution(self, app):
        """Return: {'new_point': new_point, 'error': error_mm, 'imagen': encoded_image}}"""
        # Execute detection
        print("Executing detection...")
        self.plc_client.cam_states['RUNNING'] = True
        self.plc_client.cam_states['READY'] = False
        
        # Process app
        app = f"app{app:02d}"

        # Get index from the "names" area inside "cameras": "cam02" -> 2, make a list with that if they are enabled
        cam_list = [int(cam["name"][3:]) for cam in self.config[app]['cameras'] if self.config['cameras'][int(cam["name"][3:])]['enabled'] ]
        
        # Execute detection
        result_list = self.camera_manager.execute_detection(cam_list)
        print(f"Detection executed: {result_list}")

        # Process indexes and differences
        cameras = self.config[app]['cameras']
        differences = []
        for index in cam_list:
            print(f"\t-> Camera {index}:", end=" ")
            name = f"cam{index:02d}"
            # Get the camera dictionarie from the selected app by name
            cam = [cam for cam in cameras if cam['name'] == name][0]

            # Verify plc cut order
            result_list[index][1]['merma'] = self.plc_client.plc_states['TRIG_CUT']
            if self.plc_client.plc_states['TRIG_CUT'] == True:
                print("\t-> Merma ON")
                set_point = cam['set-merma']
            else:
                print("\t-> Merma OFF")
                set_point = cam['set-point']                
            result_list[index][1]['set_point'] = set_point
            
            # Get the result from the result_list by index
            result = result_list[index] 
            if result[0] == 0:
                if abs(result[1]['y'] - set_point) <= 25:
                    diff = 0
                    differences.append(diff)
                    continue
                 
                if result[1]['y'] > set_point:
                    diff = result[1]['y'] - set_point
                    print(f"\t\t-> Operation: {diff} = {result[1]['y']} - {set_point}")
                elif result[1]['y'] < set_point:
                    diff =  result[1]['y'] + self.config[app]['nudo']/self.config['scale']['pix2mm'] - set_point
                    print(f"\t\t-> Operation: {diff} = {result[1]['y']} + {self.config[app]['nudo']/self.config['scale']['pix2mm']} - {set_point}")    
                # Differences
                result_list[index][1]['diff'] = diff
                differences.append(diff)
        
        # Align error --------------------------------------------------
        

        # Process differences
        differences = self.eliminar_outliers(differences)
        print(f"\t-> Differences out: {differences}")
        # Calculate error   
        error = sum(differences)/len(differences) if len(differences) > 0 else 0
        error_mm = error * self.config['scale']['pix2mm']
        new_point = self.plc_client.plc_struct['PV_POS'] + error_mm/10
        print(f"-> NewPoint: {new_point}, PV_POS: {self.plc_client.plc_struct['PV_POS']}, Error: {error_mm} mm")

        # Get images 
        resp_images = self.camera_manager.get_images(cam_list)
        # Process images
        jpg_images = self.image_manager.generate_images(resp_images)
        jpg_images = self.image_manager.proc_image(jpg_images, result_list)
        img_path = os.path.join(os.path.dirname(__file__), r'lib/img')
        # self.image_manager.save_images(jpg_images, path=img_path)
        self.image_manager.save_image(jpg_images, path=img_path)
        
        with open(img_path + f"/all.jpg", "rb") as f:
            image_data = f.read()
        # Encode image data as base64 string
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        print("-> Images captured : DONE")
        
        self.plc_client.cam_states['RUNNING'] = False
        self.plc_client.cam_states['READY'] = True
        return {'new_point': new_point, 'error': error_mm, 'imagen': encoded_image, 'results_cam': result_list}

    def main(self):        
        # Release threads
        self.plc_client.start_reading()
        
        self.prev_state = False
        self.plc_client.cam_states['RUNNING'] = False
        self.plc_client.cam_states['READY'] = True
        while self.run:
            # make a beat for cameras 
            # if time.time() - self.timer > self.beat_time:
                # self.timer = time.time()
                # resp = self.camera_manager.heart_beat()
                # print("Heart beat:", self.plc_client.cam_states) 

            # check trigger
            if self.plc_client.plc_states["TRIG"] == False:
                self.prev_state = False
                self.plc_client.cam_states['READY_CUT'] = False


            # Excetute detection trigger
            if self.plc_client.plc_states["TRIG"] ^ self.prev_state:                
                # Execute detection
                # resp = self.detection_execution(self.plc_client.plc_struct['PROD_TYPE']) # returns a dictionarie
                resp = self.detection_execution(4) # returns a dictionarie
                # Send to plc
                self.plc_client.cam_struct["SP_POS"] = resp['new_point']
                self.plc_client.cam_struct["SP_VEL"] = 15
                self.plc_client.cam_struct["Error"] = resp['error']
                # Update states    
                self.prev_state = self.plc_client.plc_states["TRIG"]
                self.plc_client.cam_states['READY_CUT'] = True
                
    def web_requests(self, app):

        @app.route('/connect', methods=['POST'])
        def web_connect():
            data = request.get_json()
            
            # Save data into config file
            self.config['cameras'] = data['cameras']
            self.config['plc'] = data['plc']

            # Save config
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)

            # Load config
            self.config = self.load_config()

            return {'status': 'ok'}


        @app.route('/disconnect', methods=['POST'])
        def web_disconnect():
            # Connections
            print("Disconnecting devices...")

            # Disconnect cameras
            # self.camera_manager.disconnect()

            # Disconnect plc
            # self.plc_client.stop_reading()
            # self.plc_client.disconnect_plc()

            return {'status': 'ok'}
        
        @app.route('/execute_detection', methods=['POST'])
        def web_execute_detection():
            # Execute detection
            # print(f"Detection executed: {resp}")
            data = request.get_json()
            camAppState = int(data.get('camAppState'))
            resp = self.detection_execution(camAppState)
            print(f"Detection executed")

            return {'status': 'ok', 'imagen': resp['imagen'], 'error': resp['error'], 'new_point': resp['new_point'], 'results_cam': resp['results_cam']} 
        
        # Socketio events ----------------------------------------------
        # @socketio.on('connect')
        # def socket_connect():
        #     print('Client connected')
        #     emit('connect-response', {'response': self.config['cameras']})
        

if __name__ == "__main__":
    app = AlambresWebApp()
    print(f"Connected devices: {app.camera_manager.proxies}")
    app.detection_execution(2)

