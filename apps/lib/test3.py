from snap_client import PLCDataSender

# plc = PLCDataSender()

# # method to connect
# con = plc.connect_plc(ip='192.168.0.1')

# # test reading
# # plc.db_read_num = 19
# # plc.db_read_size = 6
# # # method to read data
# # plc.read_plc_data()

# # print(plc.plc_struct)

# test write
# plc.db_write_num = 20

# plc.cam_struct['STW'] = 1
# plc.cam_struct['SP_POS'] = 2
# plc.cam_struct['SP_VEL'] = 3
# plc.cam_struct['Error'] = 4

# print(plc.cam_struct)
# plc.send_plc_data()


# des = plc.disconnect_plc()

import snap7

plc = snap7.client.Client()
plc.connect('192.168.0.1', 0, 1)

print(plc.get_connected())

try:
    data = plc.db_read(19, 0, 6)
    print("DATA: ", data)

except RuntimeError as e:
    print("Error Runtime: ", e)

finally:
    error = plc.disconnect()
    print(f"Diconnect Error: {error}")