import threading
# from .http_client import HTTPDataSender
from snap7 import client, util

        
class PLCDataSender():

    cam_states = {
        "CAM1_CON"  : False,
        "CAM2_CON"  : False,
        "CAM3_CON"  : False,
        "CAM4_CON"  : False,
        "CAM1_Err"  : False,
        "CAM2_Err"  : False,
        "CAM3_Err"  : False,
        "CAM4_Err"  : False,
        "RUNNING"   : False,
        "PAUSE"     : False,
        "RESET"     : False,
        "STOP"      : False,
        "ErrAlig"   : False,
        "ErrProc"   : False,
        "None"      : False,
        "None"      : False,
    }

    cam_struct = {
        "STW"       : 0,
        "SP_POS"    : 0,
        "SP_VEL"    : 0,
        "Error"     : 0
    }

    plc_states = {
        "TRIG"      : False,
        "RESET"     : False,
        "None"      : False,
        "None"      : False,
        "None"      : False,
        "None"      : False,
        "None"      : False,
        "None"      : False,
        "None"      : False,
        "None"      : False,
        "None"      : False,
        "ErrAlig"   : False,
        "ErrProc"   : False,
        "None"      : False,
        "None"      : False,
        "None"      : False,
    }

    plc_struct = {
        "STW"   : None,
        "Var_1" : 0,
        "Var_2" : 0,
    }

    def __init__(self):
        self.ip = None
        self.rack = 0
        self.slot = 1
        self.plc = None
        self.data_control = None
        self.data_send = None
        self.db_write_num = 20
        self.db_read_num = 19
        self.db_read_size = 6

    def __del__(self):
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
        

    def read_plc_data(self) -> dict:
        """ Read data from plc and convert to plc struct
            Returns:
                dict: plc struct
        """
        self.data_control = self.plc.db_read(self.db_read_num, 0, self.db_read_size)
        self.plc_struct["STW"] = util.get_word(self.data_control, 0)
        self.plc_struct["Var_1"] = util.get_int(self.data_control, 2)
        self.plc_struct["Var_2"] = util.get_int(self.data_control, 4)
        return self.plc_struct

    def send_plc_data(self) -> None:
        """ Convert cam states to cam struct and cam struct to <<data send>>"""
        self.data_send = bytearray()
        # Cam states to cam struct['STW']
        self.cam_struct["STW"] = 0
        for i, (key, value) in enumerate(self.cam_states.items()):
            if value:
                self.cam_struct["STW"] |= 1 << i
        # Cam struct to data send
        util.set_word(self.data_send, 0, self.cam_struct["STW"])
        util.set_int(self.data_send, 2, self.cam_struct["SP_POS"])
        util.set_int(self.data_send, 4, self.cam_struct["SP_VEL"])
        util.set_int(self.data_send, 6, self.cam_struct["Error"])
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


