from flask import Flask, Response, render_template
import os
import cv2
import time
import json
import threading
import numpy as np
from 
from flask import request


class AlambresWebApp:
    def __init__(self, camera_manager=None, plc_client=None, image_manager=None, socket=None):
        self.camera_manager = camera_manager
        self.plc_client = plc_client
        self.image_manager = image_manager
        self.socket = socket
        # Thread
        self.process = None
        # read lib/config.json
        self.config_path = os.path.join(os.path.dirname(__file__), 'lib/config.json')
        self.config = self.load_config()

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

    def check_connection(self):
        # Check Camera and PLC
        pass

    def main(self):
        self.prev_state = False
        while True:
            
            # 
            pass    
    
    def start_web_app(self, app):
        pass


if __name__ == "__main__":
    app = AlambresWebApp()
    print(app.config['app00']['compensation'])
    app = 10
    #convert to 'app00'
    app = f"app{app:02d}"
    print(app)

