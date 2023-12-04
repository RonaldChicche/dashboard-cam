import xmlrpc.client
import concurrent.futures
import xml
import threading
import socket
import time


# This function will return the IP address of the device even when it is conncted to a VPN
def get_ip_address(refference_ip, refference_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((refference_ip, refference_port))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address

class XmlRpcCameraProxy:

    def __init__(self, ip:str, port:int=8080, timeout:float=30):
        self.ip             = ip
        self.user_ip        = get_ip_address(ip, port)
        self.url            = f"http://{ip}:{port}/RPC2"
        self.stream_url     = f"udp://{ip}:50002"
        self.proxy = xmlrpc.client.ServerProxy(self.url)
        self.test_config = [0]
        socket.setdefaulttimeout(timeout)

    def __getattr__(self, name):
        """
        Allows to call the methods of the proxy directly
        """
        return getattr(self.proxy, name)
    
    def __del__(self):
        self.disconnect()

    def disconnect(self):
        if self.test_config[0] == 0:
            self.test_config = self.proxy.xmlTestConfig(0)
        resp = self.proxy.xmlDisconnect(self.user_ip)
        if resp[0] == 0:
            print(f"Disconnected from {self.ip}")
        else:
            error_msg = f"Error disconnecting from {self.ip}: {resp[1]}"
            raise Exception(error_msg)

    def connect(self, platform):
        """ Input: platform, automatic
        Returns: [connection, set_cfg, {'model', 'ip', 'mac'}]"""

        self.profile = {}
        try:
            resp = self.proxy.xmlConnect(self.user_ip, platform)
            if resp[0] == 0:
                self.profile['model'] = resp[3]
                network_params = self.get_network_parameters()
                self.profile['ip'] = network_params['ip']
                self.profile['mac'] = network_params['mac']
                self.init_config()
                set_cfg = self.set_config(0)
                return [0, set_cfg, self.profile]
            else:
                print(f"Error connecting to {self.ip}: {resp[0]}")
                return [1]
        except socket.timeout:
            print(f"Timeout connecting to {self.ip}")
            return [1]

    def get_compaitble_versions(self):
        resp = self.proxy.xmlGetCompatibleCPVersions()
        if resp[0] == 0:
            self.num_versions = resp[1]
            self.compatible_versions = resp[2:]
            print(f"Compatible versions: {self.compatible_versions}")
        else:
            print(f"Error getting compatible versions: {resp[0]}")
    
    def get_network_parameters(self):
        network_params = {}
        resp = self.proxy.xmlGetNetworkParameters()
        if resp[0] == 0:
            network_params['ip'] = resp[2]
            network_params['subnet'] = resp[3]
            network_params['gateway'] = resp[4]
            network_params['http_port'] = resp[5]
            network_params['udp_port'] = resp[6]
            network_params['mac'] = resp[7]
            # pcic = self.proxy.xmlGetPcicTcpConfig()
            # if pcic[0] == 0:
            #     network_params['pcic_port'] = pcic[1]
            # else:
            #     network_params['pcic_port'] = None

            self.ip = network_params['ip']
            self.subnet = network_params['subnet']
            self.gateway = network_params['gateway']
            self.http_port = network_params['http_port']
            self.udp_port = network_params['udp_port']
            self.mac = network_params['mac']
            # self.pcic_port = network_params['pcic_port']
        else:
            print(f"Error getting network parameters: {resp[0]}")  
        
        return network_params

    def init_config(self):
        try:
            resp = self.proxy.xmlGetConfigList()
            # if resp[0] == 0:
            self.available_configs = resp[1]
            self.size_configs = resp[3]
            self.config_id = resp[4] # this is the only attribute that i know what is ... i thinnk
            self.config_parameters = []
            keys = ['name', 'id', 'size', 'num_config', 'list_config']
            # skip the first 4 elements and save in gruoups of 5 with a key the rest
            for i in range(4, len(resp), 5):
                self.config_parameters.append(dict(zip(keys, resp[i:i+5])))
            return 0
        except socket.timeout:
            print(f"Error getting configuration list: {self.ip}")
            return 1

    def set_config(self, config_id):
        found = False
        for conf in self.config_parameters:
            if conf['id'] == config_id:
                self.session = conf
                found = True
                break
        if found:
            try: 
                # print(f'<{self.ip}> Init config: ', end='')
                self.open_config = self.proxy.xmlOpenConfiguration(self.session['name'], self.session['id'])
                # print(self.open_config, end='')
                return 0
            except socket.timeout:
                print(f"Error setting configuration: {config_id}")
                return 1
        else:
            print(f"Error setting configuration: {config_id}")
            return 1

    def detection(self):
        result = {}
        # print(f'<{self.ip}> Execute detection: ', end='')
        resume_results = self.proxy.xmlResumeResults()
        # print(f'Res:{resume_results}', end='')
        trigger = self.proxy.xmlExecuteTrigger()
        # print(f'Trigger: {trigger}')
        poll_results = [0,0]
        while poll_results[1] == 0:
            poll_results = self.proxy.xmlPollResults()
        # print(f'\tPoll: {poll_results[1]}', end=' -> ')
        config_results = self.proxy.xmlGetConfigRunResults()
        # print(f'<{self.ip}> Conf Res: {config_results}')
        if config_results[1] == 0:
            raise ValueError(f"Error executing detection: {config_results[1]}")
        self.last_detection = self.proxy.xmlGetConfigInstances(1)
        if self.last_detection[0] == 0:
            # type result [0, 1, [1, 'Ak0xAw__', 260.440002, 0.959605, 335.676086, 87.168205, 0.908069, 17, 627, 455, 57, 79], 322.972]
            if isinstance(self.last_detection[2][0], str):
                cor = -1
            else:
                cor = 0 

            result['id_app'] = self.last_detection[2][1 + cor]
            result['cal_time'] = self.last_detection[2][2 + cor]
            result['orientation'] = self.last_detection[2][3 + cor]
            result['x'] = self.last_detection[2][4 + cor]
            result['y'] = self.last_detection[2][5 + cor]
            result['confidence'] = self.last_detection[2][6 + cor]
            result['error'] = 0
            print(self.ip, self.last_detection)
            return [0, result]
        else:
            return [1]
        
    def execute_detection(self, tries=2):
        self.test_config = self.proxy.xmlTestConfig(1)
        while tries > 0:
            try:
                result = self.detection()
                self.test_config = self.proxy.xmlTestConfig(0)
                # print(result)
                return result
            except socket.timeout:
                tries -= 1
                print(self.ip, " -> Timeout, trying again...")
                
            except ValueError as e:
                # print(e)
                tries -= 1
                # print("ValueError, trying again...")
                
        
        self.test_config = self.proxy.xmlTestConfig(0)
        result = {}
        result['error'] = 1
        # print(result)
        return [1, result]
    
    def get_images(self):
        try:
            self.current_image = self.proxy.xmlGetCurrentImage()
            return self.current_image[1].data
        except xml.parsers.expat.ExpatError:
            # Maneja el error aquí
            print("Error al obtener la imagen de la cámara")
            return None
    
    def heart_beat(self):
        return self.proxy.xmlHeartbeat()[0]
    
    def poll(self):
        return self.proxy.xmlPollResults()
        
# import xmlrpc.client    -->  para evitar cruce de peticiones crea conexion nueva

# class MyXMLRPCClient:
#     def __init__(self, url):
#         self.url = url

#     def xmlHeartbeat(self):
#         with xmlrpc.client.ServerProxy(self.url) as proxy:
#             return proxy.xmlHeartbeat()

# # En tu código, reemplaza `self.proxy.xmlHeartbeat()` con:
# client = MyXMLRPCClient(url)
# return client.xmlHeartbeat()



class XmlRpcProxyManager:

    def __init__(self):
        self.platform = "3.5.0061"
        self.port = 8080
        self.proxies = []

    def __getitem__(self, index):
        """
        Returns the proxy at the given index
        proxy = proxy_manager[0] 
        """
        return self.proxies[index]

    def __len__(self):
        """
        Returns the number of proxies
        len(proxy_manager)
        """
        return len(self.proxies)
    
    def __iter__(self):
        """
        Returns an iterator over the proxies
        for proxy in proxy_manager:
            print(proxy)
        """
        return iter(self.proxies)
    
    def connect(self, ip_list:list, enable_index:list):
        self.ip_list = ip_list
        self.proxies = [XmlRpcCameraProxy(self.ip_list[i], self.port) for i in range(len(self.ip_list)) if i in enable_index]
        for i in range(len(self.ip_list)):
            if i not in enable_index:
                self.proxies.insert(i, None)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.proxies)) as executor:
            futures = [executor.submit(proxy.connect, self.platform) for proxy in self.proxies if proxy is not None]
        results = [None, None, None, None]    
        for i, future in enumerate(futures):
            results[enable_index[i]] = future.result()  
                 
        return results
    
    def disconnect(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.proxies)) as executor:
            futures = [executor.submit(proxy.disconnect) for proxy in self.proxies if proxy is not None]
            results = [future.result() for future in futures]
        return results

    def get_compaitble_versions(self):
        for proxy in self.proxies:
            proxy.get_compaitble_versions()

    def init_config(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.proxies)) as executor:
            futures = [executor.submit(proxy.init_config) for proxy in self.proxies if proxy is not None]
            results = [future.result() for future in futures]
        return results
    
    def set_config(self, config_id):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.proxies)) as executor:
            futures = [executor.submit(proxy.set_config, config_id) for proxy in self.proxies if proxy is not None]
            results = [future.result() for future in futures]
        return results

    def execute_detection(self, cam_list, tries=2):
        if len(cam_list) == 0:
            return [None, None, None, None]

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(cam_list)) as executor:
            # cam_list es una lista de indeces de las camaras que se van a usar
            selected_proxies = [self.proxies[cam] for cam in cam_list]
            futures = [executor.submit(proxy.execute_detection) for proxy in selected_proxies if proxy is not None]
            # put the results in a list in the same index as the cam_list
            results = [None, None, None, None]
            for i, future in enumerate(futures):
                results[cam_list[i]] = future.result()
        
        return results
    
    def get_images(self, cam_list):
        if len(cam_list) == 0:
            return [None, None, None, None]
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(cam_list)) as executor:
            # Usar solo los primeros 'cam' proxies
            selected_proxies = [self.proxies[cam] for cam in cam_list]
            print("Selected proxies img ", selected_proxies)
            futures = [executor.submit(proxy.get_images) for proxy in selected_proxies if proxy is not None]
            results = [None, None, None, None]
            for i, future in enumerate(futures):
                results[cam_list[i]] = future.result()
        return results
    
    def heart_beat(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.proxies)) as executor:
            futures = [executor.submit(proxy.heart_beat) for proxy in self.proxies]
            results = [future.result() for future in futures]
        return results

    def poll(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.proxies)) as executor:
            futures = [executor.submit(proxy.poll) for proxy in self.proxies]
            results = [future.result() for future in futures]
        return results