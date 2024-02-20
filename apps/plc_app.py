import os
import time
import json
import threading
import base64
import numpy as np
from scipy.stats import linregress
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
    
    def detectar_outliers(self, lista, num_desviaciones=1):
        media = sum(lista) / len(lista)
        desviacion_estandar = (sum((x - media) ** 2 for x in lista) / len(lista)) ** 0.5
        outliers = [x for x in lista if abs(x - media) > num_desviaciones * desviacion_estandar]
        return outliers

    def calcular_pendiente(self, lista_ajustada, list_index):
        # list of pos from cameras from config
        # lista_pos = [self.config['cameras'][i]['pos'] for i in list_index]
        if len(lista_ajustada) <= 1:
            return 0
        x = np.arange(len(lista_ajustada))
        # x = np.array(lista_pos)
        y = np.array(lista_ajustada)
        print(f"lista_pos: {list_index}")
        print(f"x: {x}, y: {y}")
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        return slope

    def ajustar_outliers(self, lista, compensacion, set_point, num_desviaciones=1):
        if len(lista) < 3:
            if len(lista) == 2 and abs(lista[0] - lista[1]) < 0.9 * compensacion:
                return lista
            return [min([x + compensacion, x - compensacion, x], key=lambda y: abs(y - set_point)) for x in lista]

        outliers = self.detectar_outliers(lista, num_desviaciones)
        lista_sin_outliers = [x for x in lista if x not in outliers]
        mediana = np.median(lista_sin_outliers)

        # Ajustar outliers y elegir el valor más cercano a la mediana(prom)
        outliers_ajustados = []
        for outlier in outliers:
            ajuste_suma = outlier + compensacion
            ajuste_resta = outlier - compensacion
            ajuste_cercano = min([ajuste_suma, ajuste_resta, outlier], key=lambda x: abs(x - set_point))
            outliers_ajustados.append(ajuste_cercano)

        # Reemplazar outliers en la lista original
        lista_ajustada = lista.copy()
        for outlier, ajustado in zip(outliers, outliers_ajustados):
            idx = lista_ajustada.index(outlier)
            lista_ajustada[idx] = ajustado
        
        return lista_ajustada
    
    def generate_images(self, cam_list, result_list):
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
        return encoded_image

    def process_results(self, result_list, cam_list, app, compensator):
        set_key = 'set-point'
        # Promedio de setpoints para detectar outliers
        prom_set_point = sum([cam[set_key] for cam in self.config[app]['cameras']])/len(self.config[app]['cameras'])         

        # Make a list of y coordinates from the result_list
        y_list = [result[1]['y'] for result in result_list if result is not None and result[0] == 0]
        print(f"y_list: {y_list}")
        # Detect outliers
        outliers = self.ajustar_outliers(y_list, compensator, prom_set_point)
        print(f"outliers: {outliers}")

        # Process indexes and differences
        cameras = self.config[app]['cameras']
        #
        compensar = True if sum(outliers)/len(outliers) < prom_set_point else False
        # colocar None en la posicion de las camaras deshabilitadas en outliers
        for i, val in enumerate(result_list):
            if val is None:
                outliers.insert(i, None)
                continue
            if val[0] != 0:
                outliers.insert(i, None)  
        print(f"outliers new: {outliers}")

        differences = []
        diff_ind = []
        print(cam_list)
        for index in cam_list:
            print(f"\t-> Camera {index}:", end=" ")
            name = f"cam{index:02d}"
            # Get the camera dictionarie from the selected app by name
            cam = [cam for cam in cameras if cam['name'] == name][0]

            # Set point
            set_point = cam[set_key] 
            result_list[index][1]['set_point'] = set_point
            
            # Get the result from the result_list by index
            result = outliers[index]   
            if result is None:
                print(f"None")
                continue
                
            diff = result - set_point
            print(f"\t\t-> Operation: {diff} = {result} - {set_point}")           
            
            differences.append(diff)
            diff_ind.append(index)
        
        # Si mas de la mitad son valores None levantar el align erro
        if len([x for x in outliers if x is not None]) < len(outliers)/2:
            return [], []

        return differences, diff_ind
    
    def detection_execution(self, app):
        """Return: {'new_point': new_point, 'error': error_mm, 'imagen': encoded_image}}"""
        # Execute detection
        print("Executing detection...")
        print(f"PLC: {self.plc_client.plc_states}")
        
        # Process app
        app = f"app{app:02d}"
        compensator = self.config[app]['nudo']/self.config['scale']['pix2mm']

        # Get index from the "names" area inside "cameras": "cam02" -> 2, make a list with that if they are enabled
        cam_list = [int(cam["name"][3:]) for cam in self.config[app]['cameras'] if self.config['cameras'][int(cam["name"][3:])]['enabled'] ]
        disabled_list = [index for index, cam in enumerate(self.config[app]['cameras']) if not self.config['cameras'][int(cam["name"][3:])]['enabled']]
        
        # Execute detection
        result_list = self.camera_manager.execute_detection(cam_list)

        # Verify plc cut order
        merma = self.plc_client.plc_states['TRIG_CUT']
        if merma == True:
            print("\t-> Merma ON -------------------------")
            set_key = 'set-merma'
            new_point = self.config[app]['merma'] / 10
            error_mm = 0
            align = 0
            encoded_image = None
        else:
            print("\t-> Merma OFF -------------------------")
            set_key = 'set-point'  
            differences, diff_ind = self.process_results(result_list, cam_list, app, compensator)
            # Si differences esta vacio, no se procesa
            if len(differences) == 0:
                print("No differences")
                self.plc_client.cam_states["ErrAlig"] = True
                encoded_image = self.generate_images(cam_list, result_list)

                return {'new_point': 0, 'error': 0, 'imagen': encoded_image, 'align': 0, 'results_cam': result_list}
            # Align
            align = self.calcular_pendiente(differences, diff_ind)
            if abs(align) > self.config[app]['align']:
                self.plc_client.cam_states["ErrAlig"] = True
            print(f"align: {align}")
            # Calculate error   
            error = sum(differences)/len(differences) if len(differences) > 0 else 0
            error_mm = error * self.config['scale']['pix2mm']
            print(f"New differences: {differences}")
            # New point
            new_point = self.plc_client.plc_struct['PV_POS'] + error_mm / 10

            encoded_image = self.generate_images(cam_list, result_list)
            print("-> Images captured : DONE")
        
        print(f"-> NewPoint: {new_point}, PV_POS: {self.plc_client.plc_struct['PV_POS']}, Error: {error_mm} mm")

        return {'new_point': new_point, 'error': error_mm, 'imagen': encoded_image, 'align': align, 'results_cam': result_list}

    def main(self):        
        # Release threads
        self.plc_client.start_reading()
        
        self.prev_state = False
        self.plc_client.cam_states['RUNNING'] = False
        self.plc_client.cam_states['READY'] = True
        while self.run:
            # check trigger
            trig = self.plc_client.plc_states["TRIG"] 
            if trig == False:
                self.prev_state = False
                self.plc_client.cam_states['RUNNING'] = False
                self.plc_client.cam_states['READY'] = True
                self.plc_client.cam_states['READY_CUT'] = False
                self.plc_client.cam_states["ErrAlig"] = False
                self.plc_client.cam_states["ErrProc"] = False
                self.plc_client.cam_states["Cam1_Err"] = False
                self.plc_client.cam_states["Cam2_Err"] = False
                self.plc_client.cam_states["Cam3_Err"] = False
                self.plc_client.cam_states["Cam4_Err"] = False

            # Excetute detection trigger
            if trig ^ self.prev_state:   
                
                self.plc_client.cam_states['RUNNING'] = True
                self.plc_client.cam_states['READY'] = False     
                # Update plc data
                # self.plc_client.read_plc_data()
                # Execute detection
                resp = self.detection_execution(self.plc_client.plc_struct['PROD_TYPE']) # returns a dictionarie
                # resp = self.detection_execution(5) # returns a dictionarie
                # Send to plc
                self.plc_client.cam_struct["SP_POS"] = resp['new_point']
                self.plc_client.cam_struct["SP_VEL"] = 15
                self.plc_client.cam_struct["Error"] = resp['error']
                # Update states    
                self.prev_state = True # self.plc_client.plc_states["TRIG"]
                
                self.plc_client.cam_states['RUNNING'] = False
                self.plc_client.cam_states['READY'] = True
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

            return {'status': 'ok', 'imagen': resp['imagen'], 'error': resp['error'], 'new_point': resp['new_point'], 'align': resp['align'], 'results_cam': resp['results_cam']} 
        
        # Socketio events ----------------------------------------------
        # @socketio.on('connect')
        # def socket_connect():
        #     print('Client connected')
        #     emit('connect-response', {'response': self.config['cameras']})
        

if __name__ == "__main__":
    app = AlambresWebApp()
    print(f"Connected devices: {app.camera_manager.proxies}")
    app.detection_execution(2)

