from flask import Flask, Response, render_template
import os
import cv2
import time
import numpy as np
from flask import request
# from .CamAIClass import CamAI
from onvif2 import ONVIFCamera, ONVIFService, ONVIFError


class PTZWebApp:
    def __init__(self):
        self.url = 0
        self.presets = None
        self.current_preset = None
        self.velocity = 1
        self.num_im = 0
        self.video_capture = None
        self.connected = False
        self.current_file_path = os.path.dirname(os.path.abspath(__file__))

    def start_video_capture(self, data:dict):
        if self.connected == False:
            self.ip = data['ip']
            self.user = data['user']
            self.password = data['pass']
            self.url = f'rtsp://{self.user}:{self.password}@{self.ip}'
            self.wsdl_dir = os.path.join(self.current_file_path, 'python-onvif2-zeep', 'wsdl')
            self.onvif_cam = ONVIFCamera(self.ip, 80, self.user, self.password, wsdl_dir=self.wsdl_dir)
            print(f"ONVIF: {self.onvif_cam}")
            self.ptz_service = self.onvif_cam.create_ptz_service()
            self.media_service = self.onvif_cam.create_media_service()
            self.imaging_service = self.onvif_cam.create_imaging_service()
            self.cam_token = self.media_service.GetProfiles()[0].token
            self.vid_token = self.media_service.GetVideoSources()[0].token
            print(f"Connecting to {self.url} ...")
            self.video_capture = cv2.VideoCapture(self.url)      

    def stop_video_capture(self):
        # stop video capture and onvif camera
        if self.video_capture is not None:  
            self.video_capture.release()
            self.video_capture = None
            self.connected = False

    def load_presets(self):
        self.presets = self.ptz_service.GetPresets(self.cam_token)
        list_presets = []
        if self.presets:
            print("Available PTZ presets:")
            for preset in self.presets:
                print(f"- {preset.Name}")
                list_presets.append(preset.Name)
            return list_presets
        else: 
            print("No available presets")
            return None

    def goto_preset(self, name):
        preset_name = name  # Replace with the name of the preset you want to use
        found = False
        for preset in self.presets:
            if preset.Name == preset_name:
                print(f"Moving to {preset_name} ...", end=" ")
                self.ptz_service.GotoPreset({'ProfileToken': self.cam_token, 'PresetToken': preset.token})
                print('DONE')
                found = True
        if not found:
            print(f"Preset {preset_name} not found")

    def get_state(self):
        status = self.ptz_service.GetStatus({'ProfileToken': self.cam_token})
        vid_status = self.imaging_service.GetImagingSettings({'VideoSourceToken': self.vid_token})
        print(vid_status)
        print(status)
        return status
    
    def save_preset(self):
        name = input('Ingrese nombre de nuevo preset: ')
        response = self.ptz_service.SetPreset({'ProfileToken': self.cam_token, 'PresetName': name})
        print(response)

    def set_autofocus(self):
        img_settings = self.imaging_service.GetImagingSettings({'VideoSourceToken': self.vid_token})
        img_settings.Focus.AutoFocusMode = 'AUTO'
        set_img_request = self.imaging_service.create_type('SetImagingSettings')
        set_img_request.VideoSourceToken = self.vid_token
        set_img_request.ImagingSettings = img_settings
        self.imaging_service.SetImagingSettings(set_img_request)
        print('Auto Focus mode ON')
    
    def set_velocity(self, velocity):
        if 0 <= velocity and velocity <=1:
            self.velocity = velocity
        else:
            print('Velocidad fuera de rango <min:0,max:1>')

    def move_up(self):
        print('Up')
        self.ptz_service.ContinuousMove({'ProfileToken': self.cam_token, 'Velocity': {'PanTilt': {'x': 0, 'y': self.velocity}}})
        time.sleep(0.1)
        self.ptz_service.Stop({'ProfileToken': self.cam_token})

    # Mover la cámara hacia abajo
    def move_down(self):
        #ptz = mycam.create_ptz_service()
        print('Down')
        self.ptz_service.ContinuousMove({'ProfileToken': self.cam_token, 'Velocity': {'PanTilt': {'x': 0, 'y': -self.velocity}}})
        time.sleep(0.1)
        self.ptz_service.Stop({'ProfileToken': self.cam_token})

    # Mover la cámara hacia la izquierda
    def move_left(self):
        #ptz = mycam.create_ptz_service()
        print('Left')
        self.ptz_service.ContinuousMove({'ProfileToken': self.cam_token, 'Velocity': {'PanTilt': {'x': -self.velocity, 'y': 0}}})
        time.sleep(0.1)
        self.ptz_service.Stop({'ProfileToken': self.cam_token})

    # Mover la cámara hacia la derecha
    def move_right(self):
        #ptz = mycam.create_ptz_service()
        print('Right')
        self.ptz_service.ContinuousMove({'ProfileToken': self.cam_token, 'Velocity': {'PanTilt': {'x': self.velocity, 'y': 0}}})
        time.sleep(0.1)
        self.ptz_service.Stop({'ProfileToken': self.cam_token})

    def zoom_in(self):
        print('Zoom  IN')
        self.ptz_service.ContinuousMove({'ProfileToken': self.cam_token, 'Velocity': {'PanTilt': {'x': 0, 'y': 0}, 'Zoom': -1}})
        time.sleep(0.1)
        self.ptz_service.Stop({'ProfileToken': self.cam_token})

    def zoom_out(self):
        print('Zoom OUT')
        self.ptz_service.ContinuousMove({'ProfileToken': self.cam_token, 'Velocity': {'PanTilt': {'x': 0, 'y': 0}, 'Zoom': 1}})
        time.sleep(0.1)
        self.ptz_service.Stop({'ProfileToken': self.cam_token})

    def change_url(self, url):
        self.url = url
        self.stop_video_capture()
        self.start_video_capture()

    def start(self, app):
        # Define the route for the video stream
        @app.route('/video_feed')
        def video_feed():
            def generate():
                prev_frame = None
                while True:
                    if self.video_capture is not None:
                        # Capture a frame from the video stream
                        ret, frame = self.video_capture.read()

                        if ret:
                            # Encode the frame as a JPEG image
                            ret, jpeg = cv2.imencode('.jpg', frame)

                            if ret:
                                # Yield the JPEG image as a byte stream
                                yield (b'--frame\r\n'
                                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                                prev_frame = frame
                            else:
                                print('Error encoding frame as JPEG')
                        else:
                            print('Error capturing frame from video stream')
                    else:
                        if prev_frame is not None:
                            # Create a black image of the same size as the previous frame
                            black_frame = np.zeros_like(prev_frame)

                            # Encode the black frame as a JPEG image
                            ret, jpeg = cv2.imencode('.jpg', black_frame)

                            if ret:
                                # Yield the JPEG image as a byte stream
                                yield (b'--frame\r\n'
                                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                            else:
                                print('Error encoding black frame as JPEG')
                        else:
                            print('No previous frame to use for black image')

            # Return the byte stream as a Flask response
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @app.route('/video_start', methods=['POST'])
        def video_start():
            try:
                data = dict(request.get_json())
                print(data)
                self.start_video_capture(data)
                list_presets = self.load_presets()
                print(list_presets)
                self.connected = True
                print(self.connected)
                return {'status': 200, 'presets': list_presets}
            except Exception as e:
                return {'status': 500, 'error': str(e)}

        
        @app.route('/video_stop')
        def video_stop():
            try:
                self.stop_video_capture()
                return {'status': 200}
            except Exception as e:
                return {'status': 500, 'error': str(e)}
        
        @app.route('/move_up')
        def move_up():
            self.move_up()
            return {'status': 200}
        
        @app.route('/move_down')
        def move_down():
            self.move_down()
            return {'status': 200}
        
        @app.route('/move_left')
        def move_left():
            self.move_left()
            return {'status': 200}
        
        @app.route('/move_right')
        def move_right():
            self.move_right()
            return {'status': 200}
        
        @app.route('/goto_preset', methods=['POST'])
        def goto_preset():
            name = request.json['name']
            self.goto_preset(name)
            return {'status': 200}

        @app.route('/change_url', methods=['POST'])
        def change_url():
            url = request.json['url']
            self.change_url(url)
            return {'status': 200}
        

    