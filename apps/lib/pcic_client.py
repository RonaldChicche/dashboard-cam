import socket
import re
import cv2
import matplotlib.image as mpimg
from io import BytesIO
from ..bin.formats import error_codes, error_solutions

class Client(object):
    def __init__(self, address, port) -> None:
        # open raw socket
        self.pcicSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.pcicSocket.connect((address, port))
        # Init V3 protocol
        try:
            self.pcicSocket.sendall(b'1000v03\r\n')
            msg = self.pcicSocket.recv(1024)
            if msg == b'1000*\r\n':
                print("V3 protocol inited succesfully")
            else:
                raise RuntimeError('Error initiating V3 protocol')
        except Exception as e:
            print(f"Error: {e}")
        self.recv_counter = 0
        self.debug = False
        self.debugFull = False

    def __del__(self):
        self.close()
        print("<SOCKET> CLOSED")

    def recv(self, number_bytes):
        """
        Read the next bytes of the answer with a defined length.

        :param number_bytes: (int) length of bytes
        :return: the data as bytearray
        """
        data = bytearray()
        while len(data) < number_bytes:
            data_part = self.pcicSocket.recv(number_bytes - len(data))
            if len(data_part) == 0:
                raise RuntimeError("Connection to server closed")
            data = data + data_part
        self.recv_counter += number_bytes
        return data

    def close(self):
        """
        Close the socket session with the device.

        :return: None
        """
        self.pcicSocket.close()

class PCICV3Client(Client):
    def read_next_answer(self):
        """
        Read next available answer.

        :return: None
        """
        # read PCIC ticket + ticket length
        answer = self.recv(16)
        # print("RAW response: ", answer, end=" ")
        ticket = answer[0:4]
        answer_length = int(re.findall(r'\d+', str(answer))[1])
        answer = self.recv(answer_length)
        # print(answer)
        return ticket, answer[4:-2]

    def read_answer(self, ticket):
        """
        Read the next available answer with a defined ticket number.

        :param ticket: (string) ticket number
        :return: answer of the device as a string
        """
        recv_ticket = ""
        answer = ""
        while recv_ticket != ticket.encode():
            recv_ticket, answer = self.read_next_answer()
        return answer

    def send_command(self, cmd):
        """
        Send a command to the device with 1000 as default ticket number. The length and syntax
        of the command is calculated and generated automatically.

        :param cmd: (string) Command which you want to send to the device.
        :return: answer of the device as a string
        """
        cmd_length = len(cmd) + 6
        length_header = str.encode("1000L%09d\r\n" % cmd_length)
        self.pcicSocket.sendall(length_header)
        # print(f'Sended -> {length_header}', end=" ")
        msg = b"1000" + cmd.encode() + b"\r\n"
        self.pcicSocket.sendall(msg)
        # print(f'{msg}')
        answer = self.read_answer("1000")
        return answer


class O2D22xPCICDevice(PCICV3Client):
    def __init__(self, ip, port) -> None:
        self.ip_address = ip
        self.port = port
        super(O2D22xPCICDevice, self).__init__(ip, port)
        
    def trigger_pulse(self):
        """
        Release the trigger and evaluate the image. No result output via process interface

        Returns
        -------
            - * Trigger was released 
            - ! Device is busy with an evaluation
              | Device is in an invalid state for the command, e.g. administer applications
              | Another trigger source has been selected for the device.
        """
        result = self.send_command('t')
        result = result.decode()
        return result
    
    def set_protocol_version(self, version=3):
        """
        Select the protocol version, the device is set as V1 by default, BUT is changed
        by this library as V3 for security reasons. See Client() class definition

        Parameters
        ---------- 
        vesion:
            2 digits for the protocol version. Only protocol version V3 is supported.
        Returns
        -------
        result : 
            - * Command was successful 
            - ! The device does not support the protocol version indicated
        """
        if str(version).isnumeric():
            version = str(version).zfill(2)
        result = self.send_command('v{version}'.format(version=version))
        result = result.decode()
        return result
    
    def select_application(self, application_number: [str, int]) -> str:
        """
        Activates the selected application.

        Parameters
        ----------
        application_number :
            2 digits for the application number.

        Returns
        -------
        result :
            - \* Successful change
            - ! The device is in an invalid state, e.g. administer applications
              | Invalid or not existing group or application number
        """
        command = 'c' + '0' + str(application_number).zfill(2)
        result = self.send_command(command)
        result = result.decode()
        return result
    
    def activate_result_output(self, digit):
        """
        Activate/deactivate the result output

        Parameters
        ----------
        digit:
            - 1 enables the result output.
            - 0 disables the result output.
            - See message T?

        Returns
        -------
        result :
            - \* Successful execution
            - ! No active application.
              | <digit> contains incorrect value.
              | The device is in an invalid state
        """
        result = self.send_command('p{state}'.format(state=str(digit)))
        result = result.decode()
        return result
    
    def transmit_image_for_evaluation(self, lenght:str, image_data):
        """
        Transmit the image to the device for evaluation

        Parameters
        ----------
        lenght:
            - <length>: character string with exactly 9 digits, interpreted 
                        as decimal number it indicates the length of the 
                        following image data in byte.
            - <image_data>: mage data format according to setting in the operating 
                            program. The image must be available with a resolution 
                            of 640x480. With the Raw image format, each pixel is 
                            coded with an 8 bit value, the bmp must be available in 
                            8 bit format.
        Returns
        -------
        result :
            - \* Successful execution
            - ? Invalid length
            - ! No application at present.
              | Application is being edited
              | The image format (BMP, RAW, etc.) does not meet the specifications.
              | Invalid image contents (image size, internal image head data).
        """
        if len(lenght) != 9 or not lenght.isdigit():
            raise ValueError('<lenght> should be an string with 9 digits')
        msg = b'i' + lenght.encode('ascii') + image_data.encode('ascii')
        result = self.send_command(msg)
        result = result.decode()
        return result

    # def Transmit the application data set to the device???

    def assigment_application_data(self):
        """
        Request the assignment of the application data from the device

        Returns
        -------
        result :
            - Syntax: 
                 <number><blank><group><number><blank>
                 <group><number><blank>...<group><number>
            - <number>: character string with 3 digits for the number of applications on the device as decimal number.
            - <group>: digit for the application group (always 0 for O2D22X).
            - <number>: two-digit character string, to be interpreted as decimal number for the application number. At first the number of the active configuration is output.
            - <blank>: individual blank
            - ! No active application
        """
        result = self.send_command('a?')
        result = result.decode()
        return result

    def request_statistics(self):
        """
        Request the statistics from the device

        Returns
        -------
        result :
            - Syntax: <total><blank><good><blank><bad>
            - <total>: total number of evaluations.
            - <good>: number of "good" evaluations.
            - <bad>: number of "bad" evaluations.
            - <blank>: individual blank.
            - ! No active application
        """
        result = self.send_command('s?')
        result = result.decode()
        return result

    def request_error_code(self):
        """
        Request the error code from the device

        Returns
        -------
        result :
            - Syntax: <code>
            - <code> is the error code, character string with 4 digits, to be interpreted as decimal number
        """
        result = self.send_command('E?')
        result = result.decode()
        return result
    
    def request_error_code_decoded(self):
        """
        Requests the current error state and error message as a tuple. with a suggestion

        Returns
        -------
        :return: 
                - Syntax: [<code>,<error_message>,<solution>] 
                - <code> Error code with 8 digits as a decimal value. It contains leading zeros. 
                - <error_message> The corresponding error message to the error code. 
                - <solution> The corresponding possible solution
                - $ Error code unknown
        """
        result = self.request_error_code()
        if result.isnumeric():
            error_message = error_codes[result]
            error_sol = error_solutions[result]
            if error_message:
                return [result, error_message, error_sol]
            return '$'
        return result
    
    def request_last_image(self):
        """
        Request the last image from the device

        Returns
        -------
        result :
            - Syntax: <length><image data>
            - <length>: Character string with exactly 9 digits, interpreted as 
                        decimal number it indicates the length of the following 
                        image data in byte.
            - ! No application at present.
              | No evaluation carried out.
              |  Sensor is working.

        Image data format according to setting in the operating program
        """
        result = self.send_command('I?')
        return result
    
    def request_last_result(self):
        """
        Request the last result from the device

        Returns
        -------
        result :
            - Syntax: 
                 <start><result><sc><match><sc><instances>
                 [<sc><model info>][<sc><image info>]<stop>
            - ! No application at present.
              | Application is being edited.
              | No results availabe yet.
        """
        result = self.send_command('R?')
        result = result.decode()
        return result

    def evaluate_image(self):
        """
        Release trigger, evaluate the image and result output via process 
        interface if output is active
        Activate the output → Enable/disable result output (p1)

        Returns
        -------
        result :
            - Syntax: 
                 <start><result><sc><match><sc><instances>
                 [<sc><model info>][<sc><image info>]<stop>
            - ! No application at present
              | Application is being edited
              | Current trigger mode set not via TCP/IP
        """
        result = self.send_command('T?')
        result = result.decode('ascii')
        print(result)
        return result
    
    def evaluate_image_decoded(self):
        trama = self.evaluate_image()
        if trama == '!':
            return trama
        else:
            parts = trama.split('#')
            parts[0] = parts[0].replace('start', '')
            parts[-1] = parts[-1].replace('stop', '')

            res_dic = {}
            res_dic['result'] = parts[0]
            res_dic['match'] = float(parts[1])
            res_dic['instances'] = int(parts[2])
            if parts[0] == "PASS":
                res_dic['index'] = int(parts[3])
                res_dic['x'] = int(parts[4])
                res_dic['y'] = int(parts[5])
                res_dic['rot'] = float(parts[6])
                res_dic['quality'] = float(parts[7])
            else:
                res_dic['index'] = None
                res_dic['x'] = None
                res_dic['y'] = None
                res_dic['rot'] = None
                res_dic['quality'] = None

        return res_dic
    
    def request_protocol_version(self):
        """
        Request the protocol version

        Returns
        -------
        result :
            - Syntax: 
                 <current><blank><min><blank><max>
            - <current>     two-digit decimal number with current version
            - <blank>       blank
            - <min>         two-digit decimal number with minimum version
            - <max>         two-digit decimal number with maximum version
        """
        result = self.send_command('V?')
        result = result.decode()
        return result
    
    def request_device_information(self):
        """
        Requests device information.

        :return: 
            - Syntax: 
                 <vendor><t><article><t><name><t><location><t><ip>
                 <subnet><t><gateway><t><MAC><t><DHCP><t><port>
            - <vendor>      IFM ELECTRONIC
            - <article>     Article designation and status, e.g. O2D220AC
            - <name>        Enter the sensor name as in the operating programn
            - <location>    Enter the sensor location as in the operating program
            - <ip>          IP address of the device
            - <subnet>      Subnet mask of the device
            - <gateway>     Gateway address of the device
            - <MAC>         MAC address of the device
            - <DHCP>        0 if DHCP is disabled, 1 if DHCP is enabled
            - <t>           Tabulator character
            - <port>        XML-RPC port number
        """
        result = self.send_command('D?')
        result = result.decode()
        return result
    
    def request_device_info_decoded(self):
        trama = self.request_device_information()
        info = trama.split('\t')
        if len(info) != 10:
            return "Invalid trama format"
        
        parsed_data = {
            'vendor': info[0],
            'article': info[1],
            'name': info[2],
            'location': info[3],
            'ip': info[4],
            'subnet': info[5],
            'gateway': info[6],
            'MAC': info[7],
            'DHCP': info[8],
            'port': info[9]
        }
        return parsed_data
    
    def request_last_bad_img(self):
        """
        Request the last "bad" image from the device

        Returns
        -------
        result :
            - Syntax: 
                 <length><image data>
            - <length>: Character string with exactly 9 digits, interpreted as 
                        decimal number it indicates the length of the following 
                        image data in byte. 
            - ! No application at present.
              | No evaluation carried out or no error occurred.
              | Sensor is working.

            Image data format according to setting in the operating program
        """
        result = self.send_command('F?')
        return result
    
    def request_image_decoded(self, result):
        if result == "0PASS":
            trama = self.request_last_image()
        elif result == "0FAIL":
            trama = self.request_last_bad_img()

        if trama == "!":
            return "!"
        
        img_hex = trama[9:]
        img = mpimg.imread(BytesIO(img_hex), format='jpg')
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        return img_rgb

