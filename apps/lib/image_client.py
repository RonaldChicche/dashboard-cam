# Class to decode, add features and convert to image ifm cam results
import io
import os
import cv2
from datetime import datetime
import matplotlib.image as mpimg
from collections import namedtuple
# from .http_client import HTTPDataSender


RED    = (255,   0,   0)
YELLOW = (255, 255,   0)
GREEN  = (  0, 255,   0)
BLUE   = (  0,   0, 255)
VIOLET = (255,   0, 255)


Objeto = namedtuple('Objeto', ['x', 'y', 'ori', 'merma', 'set_point'])

class ImageClient():
    def __init__(self):
        self.header_path = os.path.join(os.path.dirname(__file__), r'bmp_header.bin')
        # Make header
        self.header_dic = self.get_header(self.header_path)
        self.header = self.make_header(self.header_dic)
        self.img = None
        self.img_mpimg = None
        self.img_bytes = None

    def get_header(self, header_path):
        header_dic = {}
        with open(header_path, 'rb') as f:
            header = f.read()
        header_dic['signature'] = header[:2].decode()
        header_dic['file_size'] = int.from_bytes(header[2:6], 'little')
        header_dic['reserved'] = int.from_bytes(header[6:10], 'little')
        header_dic['data_offset'] = int.from_bytes(header[10:14], 'little')
        header_dic['header_size'] = int.from_bytes(header[14:18], 'little')
        header_dic['image_width'] = int.from_bytes(header[18:22], 'little')
        header_dic['image_height'] = int.from_bytes(header[22:26], 'little')
        header_dic['planes'] = int.from_bytes(header[26:28], 'little')
        header_dic['bits_per_pixel'] = int.from_bytes(header[28:30], 'little')
        header_dic['compression'] = int.from_bytes(header[30:34], 'little')
        header_dic['image_size'] = int.from_bytes(header[34:38], 'little')
        header_dic['x_pixels_per_meter'] = int.from_bytes(header[38:42], 'little')
        header_dic['y_pixels_per_meter'] = int.from_bytes(header[42:46], 'little')
        header_dic['total_colors'] = int.from_bytes(header[46:50], 'little')
        header_dic['important_colors'] = int.from_bytes(header[50:54], 'little')
        header_dic['color_palette'] = header[54:1078]
        
        return header_dic
    
    def make_header(self, parameters:dict):
        header = b'BM'
        header += parameters['file_size'].to_bytes(4, 'little')
        header += parameters['reserved'].to_bytes(4, 'little')
        header += parameters['data_offset'].to_bytes(4, 'little')
        header += parameters['header_size'].to_bytes(4, 'little')
        header += parameters['image_width'].to_bytes(4, 'little')
        header += parameters['image_height'].to_bytes(4, 'little')
        header += parameters['planes'].to_bytes(2, 'little')
        header += parameters['bits_per_pixel'].to_bytes(2, 'little')
        header += parameters['compression'].to_bytes(4, 'little')
        header += parameters['image_size'].to_bytes(4, 'little')
        header += parameters['x_pixels_per_meter'].to_bytes(4, 'little')
        header += parameters['y_pixels_per_meter'].to_bytes(4, 'little')
        header += parameters['total_colors'].to_bytes(4, 'little')
        header += parameters['important_colors'].to_bytes(4, 'little')
        header += parameters['color_palette']
        
        return header
    
    def generate_image(self, img):
        imagen_bmp = self.header + img
        imagen_jpg = mpimg.imread(io.BytesIO(imagen_bmp), format='jpg')
        
        return imagen_jpg
    
    def generate_images(self, img_data):
        imagen_list = []
        for img in img_data:
            if img is None: 
                imagen_list.append(None)
                continue
            imagen_list.append(self.generate_image(img))
        
        return imagen_list

    def proc_image(self, img_list, result_list):
        """ Process images with results from camera"""
        
        img_proc_list = [] 
        # make a bucle to process each image with each result
        for i, result in enumerate(result_list):
            if result is None or img_list[i] is None:
                img_proc_list.append(None)
                continue

            # Get size of images
            img_h, img_w = img_list[i].shape
            img_list[i] = cv2.cvtColor(img_list[i], cv2.COLOR_BGR2RGB)            
            img = img_list[i].copy()
            
            
            # Title and current time
            date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            cam = f'Camera: {i}'
            cv2.putText(img, cam, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 1)
            cv2.putText(img, date, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 1)
            
            # If no result 
            if result_list[i][0] != 0:
                img_proc_list.append(img)
                continue

            obj = Objeto(int(result_list[i][1]['x']), 
                         int(img_h - result_list[i][1]['y']), 
                         int(result_list[i][1]['orientation']),
                         result_list[i][1]['merma'],
                         result_list[i][1]['set-point'])
            # Print analysis on image
            # dx = img_w/2 - obj.x
            # dy = img_h/2 - obj.y
            dx = obj.x 
            dy = obj.y
            
            # Draw margin lines
            sp_s = (0, img_h - result_list[i][1]['set-point'])
            sp_e = (img_w, img_h - result_list[i][1]['set-point'])

            ch_s = (0, int(img_h/2))
            ch_e = (img_w, int(img_h/2))
            cv_s = (int(img_w/2), 0)
            cv_e = (int(img_w/2), img_h)

            cv2.circle(img, (obj.x, obj.y), 0, RED, 5)
            
            cv2.line(img, ch_s, ch_e, VIOLET, 1)
            cv2.line(img, cv_s, cv_e, VIOLET, 1)
            cv2.line(img, sp_e, sp_s, YELLOW, 1)
            
            # Draw difference
            ldy_s = (obj.x, obj.y)
            ldy_e = (obj.x, int(img_h/2))
            cv2.line(img, ldy_s, ldy_e, (150, 0, 150), 1)
            txt_dy = (obj.x+10, int((obj.y + img_h/2)/2))
            cv2.putText(img, f"ubic: {dy}", (txt_dy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, VIOLET, 1)

            # Draw text from results
            conf = str(round(result_list[i][1]['confidence'] * 10, 2)) + "%"
            ori = str(round(result_list[i][1]['ori'], 2))
            cv2.putText(img, conf, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 1)
            cv2.putText(img, ori, (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 1)
            img_proc_list.append(img)
        
        return img_proc_list

    def save_image(self, img_list, path):
        # order images from the list into matrix
        self.img_matrix = []
        for i in range(4):
            if img_list[i] is None:
                continue
            self.img_matrix.append(img_list[i*4:(i+1)*4])
        # concatenate images in the matrix
        self.img_concat = []
        for row in self.img_matrix:
            self.img_concat.append(cv2.hconcat(row))
        # concatenate rows
        self.img_concat = cv2.vconcat(self.img_concat)
        # save image
        cv2.imwrite(path, self.img_concat)

    def save_images(self, img_list, path):
        # save images as jpg files in the path
        for i, img in enumerate(img_list):
            if img is not None:
                cv2.imwrite(path + f"/img_{i}.jpg", img)


