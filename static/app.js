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
        // 🔥 Fetch cameras + health together
        const [cameras, health] = await Promise.all([
            fetch("/cameras").then(r => r.json()),
            fetch("/camera-health").then(r => r.json())
        ]);

        grid.innerHTML = "";

        // 🔥 Active camera IDs
        const activeIds = new Set(
            (health.active_cameras || []).map(c => c.camera_id)
        );

        // 🔥 Inactive reasons map
        const inactiveMap = {};
        (health.inactive_cameras || []).forEach(c => {
            inactiveMap[c.camera_id] = c.reason || "Inactive";
        });

        cameras.forEach((cam) => {
            const card = document.createElement("div");
            card.className = "camera";

            const isActive = activeIds.has(cam.id);

            // 🔥 Border color
            card.style.border = isActive
                ? "3px solid green"
                : "3px solid red";

            // 🔥 Status text
            const statusText = isActive
                ? "🟢 ACTIVE"
                : `🔴 INACTIVE (${inactiveMap[cam.id] || ""})`;

            card.innerHTML = `
                <canvas id="cam${cam.id}" width="640" height="360"></canvas>
                <p>${cam.name || "Camera " + cam.id}</p>
                <p style="font-size:12px;">${statusText}</p>
            `;

            grid.appendChild(card);

            // 🔥 Only start stream if camera is active
            if (isActive && !sockets[cam.id]) {
                startWebSocket(cam.id);
            }
        });

    } catch (err) {
        console.error(err);
        grid.innerHTML = "Error loading cameras";
    }
}

loadLiveCameras(); // run once

setInterval(updateCameraStatus, 5000);

async function updateCameraStatus() {
    try {
        const health = await fetch("/camera-health").then(r => r.json());

        const activeIds = new Set(
            (health.active_cameras || []).map(c => c.camera_id)
        );

        document.querySelectorAll(".camera").forEach(card => {
            const camId = parseInt(card.dataset.id);

            if (activeIds.has(camId)) {
                card.style.border = "3px solid green";
            } else {
                card.style.border = "3px solid red";
            }
        });

    } catch (e) {
        console.error(e);
    }
}

function startWebSocket(camId) {
    // 🔥 Prevent duplicate connections
    if (sockets[camId] && sockets[camId].readyState === WebSocket.OPEN) {
        return;
    }

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

    ws.onclose = () => {
        console.log(`WS closed for cam ${camId}`);

        // 🔥 Clean reference
        delete sockets[camId];

        // 🔥 Controlled reconnect
        setTimeout(() => startWebSocket(camId), 2000);
    };

    ws.onerror = (err) => {
        console.error(`WS error cam ${camId}`, err);
        ws.close();
    };
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
    const errorBox = document.getElementById("errorBox");
    const successBox = document.getElementById("successBox");
    const loader = document.getElementById("loader");

    errorBox.style.display = "none";
    successBox.style.display = "none";
    loader.style.display = "none";

    const ip = document.getElementById("ip").value.trim();
    const username = document.getElementById("user").value.trim();
    const password = document.getElementById("pass").value.trim();

    if (!ip || !username || !password) {
        errorBox.innerText = "❌ All fields are required";
        errorBox.style.display = "block";
        return;
    }

    loader.style.display = "block";

    const payload = {
        ip,
        username,
        password,
        name: document.getElementById("name").value,
        rtsp_url: document.getElementById("rtsp").value,

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

    try {
        const res = await fetch("/add_camera", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });

        let data = {};
        try {
            data = await res.json();
        } catch {}

        loader.style.display = "none";

        if (!res.ok) {
            errorBox.innerText = "❌ " + (data.detail || "Failed to connect camera");
            errorBox.style.display = "block";
            return;
        }

        successBox.innerText = "✅ Camera added successfully!";
        successBox.style.display = "block";

        setTimeout(() => {
            showCameras();
        }, 1500);

    } catch (err) {
        loader.style.display = "none";
        errorBox.innerText = "❌ Server not reachable";
        errorBox.style.display = "block";
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