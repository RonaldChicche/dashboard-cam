# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
from flask_socketio import SocketIO
from flask import request, jsonify, render_template_string

from .plc_app import AlambresWebApp
import base64


db = SQLAlchemy()
login_manager = LoginManager()


# Application
web_app = AlambresWebApp()

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

    # Web Applications ---------------------
    web_app.web_requests(app)

def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

# method to connect
def manual_devices(app):
    pass
    # @app.route('/connect', methods=['POST'])
    # def connect():
    #     data = request.get_json()
    #     # print(data)
    #     ip_plc = data['ip_plc1']
    #     ip_cam = [data['ip_cam1']]

    #     # Connections
    #     t = 3
    #     plc_con = None
    #     try:
    #         cam_con = camera_manager.connect(ip_list=ip_cam)
    #         cam_ini = camera_manager.init_config()
    #         cam_set = camera_manager.set_config(0)
    #         plc_con = plc_client.connect_plc(ip=ip_plc)

    #         # Run threads
    #         camera_manager.start_reading()
    #         plc_client.start_reading()
    #     except RuntimeError as e:
    #         print("Error: ", e)
    #         if t > 0:
    #             plc_client.disconnect_plc()
    #             plc_con = plc_client.connect_plc(ip=ip_plc)
    #             t -= 1
    #         else:
    #             print("PLC connection error")
            
    #     # check cam alive 
    #     heart_beat = camera_manager.heart_beat()
    #     print("heart beat: ", heart_beat)
        
    #     # return jsonify({'circle1': cam_con[0][0], 'circle2': cam_ini[0][0], 'circle3': cam_set[0], 'circle4': plc_con[0]})
    #     # return jsonify({'circle1': 0, 'circle2': 0, 'circle3': 1, 'circle4': 0})
    #     print("Cam_con: ", cam_con[0])
    #     print("Cam_ini: ", cam_ini[0])
    #     print("Cam_set: ", cam_set[0])
    #     print("PLC_con: ", plc_con)
    #     response = {'states': cam_con, 'init': cam_ini, 'settings': cam_set, 'plc_state': plc_con}
    #     # convert to json
    #     return jsonify(response)
    
    # # method to disconnect
    # @app.route('/disconnect', methods=['POST'])
    # def disconnect():
    #     # global camera_manager
    #     # global plc_client
    #     # Connections
    #     print("Disconnecting devices...")
    #     plc_client.stop_reading()
    #     camera_manager.stop_reading()
    #     camera_manager.disconnect()
    #     plc_client.disconnect_plc()

    #     return {'status': 'ok'}
    
    # # execute detection
    # @app.route('/execute_detection', methods=['POST'])
    # def execute_detection():
    #     # Execute detection
    #     print("Executing detection...")
    #     results = camera_manager.execute_detection(tries=2)
    #     # print_detection_result(results)
    #     diferences = [res[1]["y"] for res in results if res[0] == 0]
    #     error = sum(diferences)/len(diferences) if len(diferences) > 0 else 0
    #     set_point = 240 + error
    #     velocity = 15 # corregir

    #     # get images
    #     resp_images = camera_manager.get_images()
    #     # header_path = r"C:/Users/ronal/Documents/Projects/Prodac-ProjMallas/flask-argon-dashboard/apps/lib/bmp_header.bin"
    #     header_path = os.path.join(os.path.dirname(__file__), r'lib/bmp_header.bin')
    #     jpg_images = image_manager.generate_images(resp_images, header_path=header_path)
    #     # process imagess
    #     jpg_images = image_manager.proc_image(jpg_images, results)
    #     # save images 
    #     # img_path = r"C:/Users/ronal/Documents/Projects/Prodac-ProjMallas/flask-argon-dashboard/apps/lib/img"
    #     img_path = os.path.join(os.path.dirname(__file__), r'lib/img')
    #     image_manager.save_images(jpg_images, path=img_path)
    #     response = {'set_point': set_point, 'velocity': velocity, 'error': error}
    #     print(response)
        
    #     # read images from img_path
    #     jpg_images = []
    #     for i in range(4):
    #         with open(img_path + f"/img_{i}.jpg", "rb") as f:
    #             jpg_images.append(f.read())

    #     image_data = jpg_images[0]
    #     # Encode image data as base64 string
    #     encoded_image = base64.b64encode(image_data).decode('utf-8')
    #     return {'status': 'ok', 'image': encoded_image, 'response': response, 'results': results}

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    # socketio = SocketIO(app, logger=True, engineio_logger=True, async_mode='threading')
    register_extensions(app)
    register_blueprints(app)
    # Application
    # manual_devices(app)
    # web_app.start_thread()
    return app
