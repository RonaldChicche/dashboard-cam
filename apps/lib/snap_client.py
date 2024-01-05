import threading
# from .http_client import HTTPDataSender
from snap7 import client, util
import time

        
class PLCDataSender():

    cam_states = {
        "RUNNING"   : False,
        "PAUSE"     : False,
        "RESET"     : False,
        "STOP"      : False,
        "ErrAlig"   : False,
        "ErrProc"   : False,
        "READY"     : False,
        "READY_CUT" : False,
        "CAM1_CON"  : False,
        "CAM2_CON"  : False,
        "CAM3_CON"  : False,
        "CAM4_CON"  : False,
        "CAM1_Err"  : False,
        "CAM2_Err"  : False,
        "CAM3_Err"  : False,
        "CAM4_Err"  : False,  
    }

    cam_struct = {
        "STW"       : 0,
        "SP_POS"    : 0,
        "SP_VEL"    : 0,
        "Error"     : 0
    }

    plc_states = {
        "None0"     : False,
        "APP"       : False,
        "RESET"     : False,
        "CUT_DONE"  : False,
        "None3"     : False,
        "None4"     : False,
        "None5"     : False,
        "None6"     : False,
        "TRIG"      : False,
        "None8"     : False,
        "None9"     : False,
        "ErrAlig"   : False,
        "ErrProc"   : False,
        "None10"    : False,
        "None11"    : False,
        "None12"    : False,
    }

    plc_struct = {
        "CTW"   : None,
        "PV_POS" : 0,
        "PROD_TYPE" : 0,
    }

    def __init__(self):
        self.ip = None
        self.rack = 0
        self.slot = 1
        self.plc = None
        self.data_control = None
        self.data_send = bytearray(14)
        self.db_write_num = 20
        self.db_read_num = 19
        self.db_read_size = 8
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._read_plc_data)
        self.thread_started = False

    def __del__(self):
        self.stop_reading()
        self.disconnect_plc()

    def disconnect_plc(self):
        # verify if plc is declared
        if self.plc is not None:
            if self.plc.get_connected():
                self.plc.disconnect()
                return 0
        return 1  

    def connect_plc(self, ip):
        self.ip = ip
        if self.plc is None:
            self.plc = client.Client()
            self.plc.connect(self.ip, self.rack, self.slot)
            if self.plc.get_connected():
                return 0
        return 1        

    def _read_plc_data(self):
        """ Read data from plc and convert to plc struct
            Returns:
                dict: plc_struct
        """
        self.thread_started = True
        while not self._stop_event.is_set():
            # Inspect if it is connected to the plc
            if not self.plc.get_connected():
                self.plc.connect(self.ip, self.rack, self.slot)
                # Reconnection verification
                if not self.plc.get_connected():
                    print("PLC not connected")
                    time.sleep(1)
                continue
            # read data from plc
            self.data_control = self.plc.db_read(self.db_read_num, 0, self.db_read_size)
            word = util.get_word(self.data_control, 0)
            self.plc_struct["CTW"] = bin(word)[2:].zfill(16)        
            self.plc_struct["PV_POS"] = util.get_real(self.data_control, 2)
            self.plc_struct["PROD_TYPE"] = util.get_int(self.data_control, 6)
            # parse plc data states
            self.parse_plc_data(self.plc_struct["CTW"])
            # send data to plc
            self.send_plc_data()
            
            time.sleep(0.1)

    def start_reading(self):
        self._thread.start()

    def stop_reading(self):
        if self.thread_started:
            self._stop_event.set()
            self._thread.join()

    def parse_plc_data(self, plc_word):
        # turn ctw "00000000" in plc_states dic
        plc_word = plc_word[::-1]
        for i, (key, value) in enumerate(self.plc_states.items()):
            self.plc_states[key] = bool(int(plc_word[i]))
        return self.plc_states

    def send_plc_data(self) -> None:
        """ Convert cam states to cam struct and cam struct to <<data send>>"""
        self.data_send = bytearray(14)
        # Cam states to cam struct['STW']
        self.cam_struct["STW"] = 0
        for i, (key, value) in enumerate(self.cam_states.items()):
            if value:
                self.cam_struct["STW"] |= 1 << i
        # Cam struct to data send
        util.set_word(self.data_send, 0, self.cam_struct["STW"])
        util.set_real(self.data_send, 2, self.cam_struct["SP_POS"])
        util.set_real(self.data_send, 6, self.cam_struct["SP_VEL"])
        util.set_real(self.data_send, 10, self.cam_struct["Error"])
        # write to PLC
        self.plc.db_write(self.db_write_num, 0, self.data_send)        
            
    def read_cam_states(self, response:dict) -> None:
        """ Read cam states from response and update cam states
            Args:
                response (dict): response from process"""
        # response = {"CAM_STATES": [True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], 
        # "SP_POS": 0, 
        # "SP_VEL": 0, 
        # "Error": 0}
        # bucle for para actualizar los estados de las camaras
        for i, (key, value) in enumerate(self.cam_states.items()):
            self.cam_states[key] = response["CAM_STATES"][i]

    def read_cam_sp(self, response:dict) -> None:
        """ Read cam set point from response and update cam struct
            Args:
                response (dict): response from detection"""
        # verify if response has SP_POS, SP_VEL and Error
        response_states = ["SP_POS", "SP_VEL", "Error"]
        if all(key in response for key in response_states):
            self.cam_struct["SP_POS"] = response["SP_POS"]
            self.cam_struct["SP_VEL"] = response["SP_VEL"]
            self.cam_struct["Error"] = response["Error"]


