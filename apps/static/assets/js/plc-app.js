document.addEventListener("DOMContentLoaded", function() {
    // Connect buttons
    const connectBtn = document.getElementById('connectBtn');
    const connectBtnMobile = document.getElementById('connectBtnMobile');

    // Disconnect buttons
    const disconnectBtn = document.getElementById('disconnectBtn');
    const disconnectBtnMobile = document.getElementById('disconnectBtnMobile');

    // Execute buttons
    const executeBtn = document.getElementById('executeBtn');
    const executeBtnMobile = document.getElementById('executeBtnMobile');


    // Attach event listeners
    [connectBtn, connectBtnMobile].forEach(btn => {
        btn.addEventListener('click', function() {
            const ip_plc1 = document.getElementById('ip_plc1').value; //id="ip_cam1"
            const ip_cam1 = document.getElementById('ip_cam1').value;
            const ip_cam2 = document.getElementById('ip_cam2').value;
            const ip_cam3 = document.getElementById('ip_cam3').value;
            const ip_cam4 = document.getElementById('ip_cam4').value;
            fetch('/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ip_plc1, ip_cam1, ip_cam2, ip_cam3, ip_cam4})
            })
            .then(response => response.json())
            .then(data => {                
                // asing the values to the circles : states
                var cam_con = data.states;
                var cam_ini = data.init;
                var cam_set = data.settings;
                var plc_con = data.plc_state;
                
                // change the color of the circles :  plc1-c1
                var circle = document.getElementById('plc1-c1');
                if (plc_con == 1) {
                    circle.style.backgroundColor = "green";
                }
                else {
                    circle.style.backgroundColor = "red";
                }

                // change the color of the circles :  cam1-c1, cam2-c1, cam3-c1, cam4-c1
                for (var i = 0; i < 4; i++) {
                    var circle = document.getElementById(`cam${i+1}-c1`);
                    if (cam_con[i][0] == 0) {
                        circle.style.backgroundColor = "green";
                    }
                    else {
                        circle.style.backgroundColor = "red";
                    }
                }

                // change the color of the circles :  cam1-c2, cam2-c2, cam3-c2, cam4-c2   
                for (var i = 0; i < 4; i++) {
                    var circle = document.getElementById(`cam${i+1}-c2`);
                    if (cam_ini[i][0] == 0) {
                        circle.style.backgroundColor = "green";
                    }
                    else {
                        circle.style.backgroundColor = "red";
                    }
                }

                // change the color of the circles :  cam1-c3, cam2-c3, cam3-c3, cam4-c3
                for (var i = 0; i < 4; i++) {
                    var circle = document.getElementById(`cam${i+1}-c3`);
                    if (cam_set[i][0] == 0) {
                        circle.style.backgroundColor = "green";
                    }
                    else {
                        circle.style.backgroundColor = "red";
                    }
                }   
            })
            .catch(error => console.error(error));
        });
    });

    [disconnectBtn, disconnectBtnMobile].forEach(btn => {
        btn.addEventListener('click', function() {
            fetch('/disconnect', {
                method: 'POST'
            })
            .then(response => {
                if (response.ok) {
                    console.log('Disconnected successfully');
                    // put all the circles without color
                    for (var i = 0; i < 4; i++) {
                        for (var j = 0; i < 11, j < 4; j++) {
                            var circle = document.getElementById(`cam${i+1}-c${j+1}`);
                            circle.style.backgroundColor = "transparent";
                        }
                    }

                } else {
                    console.error('Disconnection failed');
                }
            })
            .catch(error => console.error(error));
        });
    });

    [executeBtn, executeBtnMobile].forEach(btn => {
        btn.addEventListener('click', function() {
            fetch('/execute_detection', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                const imageSrc = `data:image/jpeg;base64,${data.image}`;
                const carouselItem = document.querySelector('.carousel-item');
                carouselItem.style.backgroundImage = `url(${imageSrc})`;
                console.log('Image updated');
                console.log(`Status: ${data.status}`);
                console.log(`Response: ${JSON.stringify(data.response)}`);
                console.log(`Results: ${JSON.stringify(data.results)}`);
            })
            .catch(error => console.error(error));
        });
    });

});

// SocketIO
const socket = io.connect('http://' + document.domain + ':' + location.port);

socket.on('connect', function() {
    socket.emit('client_connected');
});

socket.on('disconnect', function() {
    console.log('Disconnected from server');
});

socket.on('connect-response', function(data) {
    console.log(`Server response: ${data.response}`);
});

