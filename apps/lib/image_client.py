# Class to decode, add features and convert to image ifm cam results
import io
import cv2
import requests
import matplotlib.image as mpimg
from collections import namedtuple
# from .http_client import HTTPDataSender

Objeto = namedtuple('Objeto', ['x', 'y', 'ori'])

class ImageClient():
    def __init__(self):
        self.img = None
        self.img_mpimg = None
        self.img_bytes = None

    def get_header(self, header_path):
        self.header_dic = {}
        with open(header_path, 'rb') as f:
            header = f.read()
        self.header_dic['signature'] = header[:2].decode()
        self.header_dic['file_size'] = int.from_bytes(header[2:6], 'little')
        self.header_dic['reserved'] = int.from_bytes(header[6:10], 'little')
        self.header_dic['data_offset'] = int.from_bytes(header[10:14], 'little')
        self.header_dic['header_size'] = int.from_bytes(header[14:18], 'little')
        self.header_dic['image_width'] = int.from_bytes(header[18:22], 'little')
        self.header_dic['image_height'] = int.from_bytes(header[22:26], 'little')
        self.header_dic['planes'] = int.from_bytes(header[26:28], 'little')
        self.header_dic['bits_per_pixel'] = int.from_bytes(header[28:30], 'little')
        self.header_dic['compression'] = int.from_bytes(header[30:34], 'little')
        self.header_dic['image_size'] = int.from_bytes(header[34:38], 'little')
        self.header_dic['x_pixels_per_meter'] = int.from_bytes(header[38:42], 'little')
        self.header_dic['y_pixels_per_meter'] = int.from_bytes(header[42:46], 'little')
        self.header_dic['total_colors'] = int.from_bytes(header[46:50], 'little')
        self.header_dic['important_colors'] = int.from_bytes(header[50:54], 'little')
        self.header_dic['color_palette'] = header[54:1078]
        return self.header_dic
    
    def make_header(self, parameters:dict):
        self.header = b'BM'
        self.header += parameters['file_size'].to_bytes(4, 'little')
        self.header += parameters['reserved'].to_bytes(4, 'little')
        self.header += parameters['data_offset'].to_bytes(4, 'little')
        self.header += parameters['header_size'].to_bytes(4, 'little')
        self.header += parameters['image_width'].to_bytes(4, 'little')
        self.header += parameters['image_height'].to_bytes(4, 'little')
        self.header += parameters['planes'].to_bytes(2, 'little')
        self.header += parameters['bits_per_pixel'].to_bytes(2, 'little')
        self.header += parameters['compression'].to_bytes(4, 'little')
        self.header += parameters['image_size'].to_bytes(4, 'little')
        self.header += parameters['x_pixels_per_meter'].to_bytes(4, 'little')
        self.header += parameters['y_pixels_per_meter'].to_bytes(4, 'little')
        self.header += parameters['total_colors'].to_bytes(4, 'little')
        self.header += parameters['important_colors'].to_bytes(4, 'little')
        self.header += parameters['color_palette']
        return self.header
    
    def generate_image(self, img, header_path):
        self.header = self.get_header(header_path)
        self.img = self.make_header(self.header) + img
        # transform to jpg
        self.img = mpimg.imread(io.BytesIO(self.img), format='jpg')
        return self.img
    
    # method to generate images from a list of images in bytes all at the same time with threads
    def generate_images(self, img_list, header_path):
        self.img_list = []
        for img in img_list:
            self.img_list.append(self.generate_image(img, header_path))
        return self.img_list

    def proc_image(self, img_list, result_list):
        """ Process images with results from camera"""
        print(result_list)
        img_proc_list = []
        # get size of images
        self.img_h, self.img_w = img_list[0].shape   
        print(img_list[0].shape)
        # get margin
        self.mx = self.img_w/2 - 200
        self.my = self.img_h/2 - 200
        # make a bucle to process each image with each result
        for i in range(len(img_list)):
            # turn image to rgb 
            img_list[i] = cv2.cvtColor(img_list[i], cv2.COLOR_BGR2RGB)
            img = img_list[i].copy()
            cam = f'Camera: {i}'
            cv2.putText(img, cam, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            if result_list[i][0] == 1:
                img_proc_list.append(img)
                continue
            obj = Objeto(int(result_list[i][1]['x']), int(self.img_h - result_list[i][1]['y']), int(result_list[i][1]['orientation']))
            # Print analysis on image
            dx = self.img_w/2 - obj.x
            dy = self.img_h/2 - obj.y
            
            # Draw margin lines
            lx_1s = (int(self.img_w/2 - self.mx), self.img_h)
            lx_1e = (int(self.img_w/2 - self.mx), 0)
            lx_2s = (int(self.img_w/2 + self.mx), self.img_h)
            lx_2e = (int(self.img_w/2 + self.mx), 0)

            ly_1s = (self.img_w, int(self.img_h/2 - self.my))
            ly_1e = (0, int(self.img_h/2 - self.my))
            ly_2s = (self.img_w, int(self.img_h/2 + self.my))
            ly_2e = (0, int(self.img_h/2 + self.my))

            ch_s = (0, int(self.img_h/2))
            ch_e = (self.img_w, int(self.img_h/2))
            cv_s = (int(self.img_w/2), 0)
            cv_e = (int(self.img_w/2), self.img_h)

            cv2.line(img, lx_1s, lx_1e, (0, 255, 0), 1)
            cv2.line(img, lx_2s, lx_2e, (0, 255, 0), 1)
            cv2.line(img, ly_1s, ly_1e, (0, 255, 0), 1)
            cv2.line(img, ly_2s, ly_2e, (0, 255, 0), 1)
            cv2.circle(img, (obj.x, obj.y), 0, (255, 0, 0), 5)
            
            cv2.line(img, ch_s, ch_e, (150, 0, 150), 1)
            cv2.line(img, cv_s, cv_e, (150, 0, 150), 1)

            # Draw difference
            ldy_s = (obj.x, obj.y)
            ldy_e = (obj.x, int(self.img_h/2))
            cv2.line(img, ldy_s, ldy_e, (150, 0, 150), 1)
            txt_dy = (obj.x+10, int((obj.y + self.img_h/2)/2))
            cv2.putText(img, f"y_diff: {dy}", (txt_dy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 0, 150), 1)

            # Draw text from results
            conf = str(result_list[i][1]['confidence'])
            cv2.putText(img, conf, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            img_proc_list.append(img)
        
        return img_proc_list

    # method to send a list of images to the server
    def post_images(self, img_list):
        self.send_data(img_list)

    def save_image(self, img_list, path):
        # order images from the list into matrix
        self.img_matrix = []
        for i in range(4):
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
        for i in range(len(img_list)):
            cv2.imwrite(path + f"/img_{i}.jpg", img_list[i])


