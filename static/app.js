const grid = document.getElementById("grid");
const camTable = document.getElementById("camTable");
const discoverBox = document.getElementById("discoverBox");

let sockets = {};

function hideAll() {
    document.getElementById("live").style.display = "none";
    document.getElementById("analytics").style.display = "none";
    document.getElementById("cams").style.display = "none";
    document.getElementById("addForm").style.display = "none";
}

function stopAllSockets() {
    Object.values(sockets).forEach(ws => ws.close());
    sockets = {};
}

function showLive() {
    hideAll();
    document.getElementById("live").style.display = "block";
    loadLiveCameras();
}

function showCameras() {
    stopAllSockets();
    hideAll();
    document.getElementById("cams").style.display = "block";
    loadCameraList();
}

function showAdd() {
    stopAllSockets();
    hideAll();
    document.getElementById("addForm").style.display = "block";
}

// ---------------- LIVE (WEBSOCKET) ----------------
async function loadLiveCameras() {
    try {
        const cameras = await fetch("/cameras").then(r => r.json());

        grid.innerHTML = "";

        cameras.forEach((cam) => {
            const card = document.createElement("div");
            card.className = "camera";

            card.innerHTML = `
                <canvas id="cam${cam.id}" width="640" height="360"></canvas>
                <p>${cam.name || "Camera " + cam.id}</p>
            `;

            grid.appendChild(card);

            startWebSocket(cam.id);
        });

    } catch (err) {
        grid.innerHTML = "Error loading cameras";
    }
}

function startWebSocket(camId) {
    const canvas = document.getElementById(`cam${camId}`);
    const ctx = canvas.getContext("2d");

    const ws = new WebSocket(`ws://${location.host}/ws/${camId}`);
    sockets[camId] = ws;

    ws.onmessage = function(event) {
        const img = new Image();
        img.src = "data:image/jpeg;base64," + event.data;

        img.onload = function() {
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        };
    };

    ws.onclose = () => console.log("WS closed for cam", camId);
}

// ---------------- CAMERA LIST (UNCHANGED) ----------------
async function loadCameraList() {
    camTable.innerHTML = "<tr><td colspan='8'>Loading...</td></tr>";

    try {
        const cameras = await fetch("/cameras").then(r => r.json());

        camTable.innerHTML = "";

        cameras.forEach((cam) => {
            const row = document.createElement("tr");

            row.innerHTML = `
                <td>${cam.id}</td>
                <td>${cam.name || ""}</td>
                <td>${cam.ip}</td>
                <td>${cam.username}</td>
                <td>$....</td>
                <td>${cam.rtsp_url || ""}</td>
                <td>
                    <button onclick="deleteCamera(${cam.id})">Delete</button>
                </td>
            `;

            camTable.appendChild(row);
        });

    } catch {
        camTable.innerHTML = "<tr><td>Error loading cameras</td></tr>";
    }
}

async function addCamera() {
    const payload = {
        ip: document.getElementById("ip").value,
        username: document.getElementById("user").value,
        password: document.getElementById("pass").value,
        name: document.getElementById("name").value,

        // 🔥 NEW METADATA
        position: {
            x: parseFloat(document.getElementById("posX").value) || 0,
            y: parseFloat(document.getElementById("posY").value) || 0,
            z: parseFloat(document.getElementById("posZ").value) || 0
        },
        orientation: {
            pan: parseFloat(document.getElementById("pan").value) || 0,
            tilt: parseFloat(document.getElementById("tilt").value) || 0,
            zoom: parseFloat(document.getElementById("zoom").value) || 1
        },
        fov: parseFloat(document.getElementById("fov").value) || 90
    };

    const res = await fetch("/add_camera", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (data.error) {
        alert("Error: " + data.error);
    } else {
        alert("Camera Added with Metadata");
        showCameras();
    }
}

async function deleteCamera(id) {
    await fetch("/delete_camera", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({id})
    });

    loadCameraList();
}

// ---------------- START ----------------
showLive();

async function testMove() {
    const res = await fetch("/move_to", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            camera_id: 1,
            target: {x: 10, y: 5, z: 0}
        })
    });

    const data = await res.json();
    console.log("PTZ:", data);
}