# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
from flask import request, jsonify, render_template_string

from .lib import XmlRpcProxyManager, PLCDataSender, ImageClient
import base64


db = SQLAlchemy()
login_manager = LoginManager()

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

def configure_database(app):

    @app.before_first_request
    def initialize_database():
        try:
            db.create_all()
        except Exception as e:

            print('> Error: DBMS Exception: ' + str(e) )

            # fallback to SQLite
            basedir = os.path.abspath(os.path.dirname(__file__))
            app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')

            print('> Fallback to SQLite ')
            db.create_all()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()

# Application
camera_manager = XmlRpcProxyManager()
plc_client = PLCDataSender()
image_manager = ImageClient()
# method to connect
def connect_devices(app):
    @app.route('/connect', methods=['POST'])
    def connect():
        data = request.get_json()
        # print(data)
        ip_plc = data['ip_plc1']
        ip_cam = [data['ip_cam1'], data['ip_cam2'], data['ip_cam3'], data['ip_cam4']]

        # Connections
        t = 3
        plc_con = None
        try:
            cam_con = camera_manager.connect(ip_list=ip_cam)
            cam_ini = camera_manager.init_config()
            cam_set = camera_manager.set_config(0)
            plc_con = plc_client.connect_plc(ip=ip_plc)
        except RuntimeError as e:
            print("Error: ", e)
            if t > 0:
                plc_client.disconnect_plc()
                plc_con = plc_client.connect_plc(ip=ip_plc)
                t -= 1
            else:
                print("PLC connection error")
            
        # check cam alive 
        heart_beat = camera_manager.heart_beat()
        print("heart beat: ", heart_beat)
        
        # return jsonify({'circle1': cam_con[0][0], 'circle2': cam_ini[0][0], 'circle3': cam_set[0], 'circle4': plc_con[0]})
        # return jsonify({'circle1': 0, 'circle2': 0, 'circle3': 1, 'circle4': 0})
        response = {'states': cam_con[0][0], 'init': cam_ini[0][0], 'settings': cam_set[0], 'plc_state': plc_con[0]}
        # convert to json
        return jsonify(response)
    
# method to disconnect
def disconnect_devices(app):
    @app.route('/disconnect', methods=['POST'])
    def disconnect():
        # global camera_manager
        # global plc_client
        # Connections
        print("Disconnecting devices...")
        camera_manager.disconnect()
        plc_client.disconnect_plc()

        return {'status': 'ok'}
    
# execute detection
def execute_detection(app):
    @app.route('/execute_detection', methods=['POST'])
    def execute_detection():
        # Execute detection
        print("Executing detection...")
        results = camera_manager.execute_detection(tries=2)
        # print_detection_result(results)
        diferences = [240 - res[1]["y"] for res in results if res[0] == 0]
        error = sum(diferences)/len(diferences) if len(diferences) > 0 else 0
        set_point = 240 + error
        velocity = 15 # corregir

        # get images
        resp_images = camera_manager.get_images()
        # header_path = r"C:/Users/ronal/Documents/Projects/Prodac-ProjMallas/flask-argon-dashboard/apps/lib/bmp_header.bin"
        header_path = os.path.join(os.path.dirname(__file__), r'lib\bmp_header.bin')
        jpg_images = image_manager.generate_images(resp_images, header_path=header_path)
        # process imagess
        jpg_images = image_manager.proc_image(jpg_images, results)
        # save images 
        img_path = r"C:/Users/ronal/Documents/Projects/Prodac-ProjMallas/flask-argon-dashboard/apps/lib/img"
        image_manager.save_images(jpg_images, path=img_path)
        response = {'set_point': set_point, 'velocity': velocity, 'error': error}
        
        # read images from img_path
        jpg_images = []
        for i in range(4):
            with open(img_path + f"/img_{i}.jpg", "rb") as f:
                jpg_images.append(f.read())

        image_data = jpg_images[0]
        # Encode image data as base64 string
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        return {'status': 'ok', 'image': encoded_image, 'response': response, 'results': results}

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    # Application
    # init_application(app)
    connect_devices(app)
    disconnect_devices(app)
    execute_detection(app)
    return app
