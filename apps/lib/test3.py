from snap_client import PLCDataSender

plc_client = PLCDataSender()
plc_client.connect_plc('192.168.0.1')

run = True
try:
    while run:
        # Read PLC data
        plc_data = plc_client._read_plc_data()
        print(plc_data)
        states = plc_client.parse_plc_data(plc_data["CTW"])
        print(states)

except RuntimeError as e:
    print("Error Runtime: ", e)

finally:
    run = False
    error = plc_client.disconnect_plc()
    print(f"Diconnect Error: {error}")