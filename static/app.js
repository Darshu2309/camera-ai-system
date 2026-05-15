const grid = document.getElementById("grid");
const camTable = document.getElementById("camTable");

let sockets = {};
let discoveredCameras = [];


// ======================================================
// HIDE ALL SECTIONS
// ======================================================

function hideAll() {

    [
        "live",
        "mapView",
        "analytics",
        "cams",
        "addForm"
    ].forEach(id => {

        const el = document.getElementById(id);

        if (el) {
            el.style.display = "none";
        }
    });
}


// ======================================================
// STOP SOCKETS
// ======================================================

function stopAllSockets() {

    Object.values(sockets).forEach(s => {

        try {
            s.ws.close();
        }
        catch {}
    });

    sockets = {};
}


// ======================================================
// SHOW LIVE
// ======================================================

function showLive() {

    hideAll();

    const el = document.getElementById("live");

    if (el) {
        el.style.display = "block";
    }

    loadLiveCameras();
}


// ======================================================
// SHOW CAMERAS
// ======================================================

function showCameras() {

    stopAllSockets();

    hideAll();

    const el = document.getElementById("cams");

    if (el) {
        el.style.display = "block";
    }

    loadCameraList();
}


// ======================================================
// SHOW MAP
// ======================================================

function showMap() {

    stopAllSockets();

    hideAll();

    const el = document.getElementById("mapView");

    if (el) {
        el.style.display = "block";
    }
}


// ======================================================
// SHOW ADD
// ======================================================

function showAdd() {

    stopAllSockets();

    hideAll();

    const el = document.getElementById("addForm");

    if (el) {
        el.style.display = "block";
    }
}


// ======================================================
// LOAD LIVE CAMERAS
// ======================================================

async function loadLiveCameras() {

    try {

        const response = await fetch("/cameras");

        const cameras = await response.json();

        grid.innerHTML = "";

        // ACTIVE COUNT
        const activeCount =
            cameras.filter(cam =>
                cam.status !== "offline"
            ).length;

        document.getElementById(
            "activeCameraCount"
        ).innerText = activeCount;

        document.getElementById(
            "trackingCount"
        ).innerText = activeCount;

        cameras.forEach(cam => {

            // =========================================
            // CAMERA STATUS
            // =========================================

            const isActive =
                cam.status !== "offline" &&
                (
                    cam.rtsp_url ||
                    cam.stream_url ||
                    cam.ip
                );

            const statusText =
                isActive ? "ACTIVE" : "OFFLINE";

            const statusColor =
                isActive ? "#00ff88" : "#ff3b3b";

            const borderColor =
                isActive ? "#00ff66" : "red";

            // =========================================
            // CAMERA CARD
            // =========================================

            const card = document.createElement("div");

            card.className = "camera";

            card.dataset.id = cam.id;

            card.style.border =
                `3px solid ${borderColor}`;

            card.innerHTML = `

                <div class="live-badge">
                    LIVE
                </div>

                <div style="
                    position:relative;
                    width:100%;
                    background:black;
                    overflow:hidden;
                    border-radius:14px 14px 0 0;
                ">

                    <canvas
                        id="cam${cam.id}"
                        width="1280"
                        height="720"
                        style="
                            width:100%;
                            height:360px;
                            background:black;
                            object-fit:cover;
                            display:block;
                        "
                    ></canvas>

                    <div
                        id="offlineOverlay${cam.id}"
                        style="
                            position:absolute;
                            inset:0;
                            display:none;
                            align-items:center;
                            justify-content:center;
                            background:rgba(0,0,0,0.85);
                            color:red;
                            font-size:28px;
                            font-weight:700;
                            z-index:10;
                        "
                    >
                        NO SIGNAL
                    </div>

                </div>

                <div style="padding:18px;">

                    <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                    ">

                        <div>

                            <div style="
                                font-size:24px;
                                font-weight:700;
                            ">
                                ${cam.description || cam.name}
                            </div>

                            <div style="
                                color:#8ca2b8;
                                margin-top:6px;
                            ">
                                Camera ID: ${cam.id}
                            </div>

                        </div>

                        <div style="
                            color:${statusColor};
                            font-weight:700;
                            font-size:18px;
                        ">
                            ${statusText}
                        </div>

                    </div>

                    <div style="
                        display:grid;
                        grid-template-columns:1fr 1fr;
                        gap:14px;
                        margin-top:20px;
                    ">

                        <div class="section">

                            <div style="
                                font-size:12px;
                                color:#8ca2b8;
                            ">
                                RANGE
                            </div>

                            <div style="
                                font-size:18px;
                                font-weight:700;
                                margin-top:4px;
                            ">
                                ${cam.coverage?.range_meters || 150}m
                            </div>

                        </div>

                        <div class="section">

                            <div style="
                                font-size:12px;
                                color:#8ca2b8;
                            ">
                                FOV
                            </div>

                            <div style="
                                font-size:18px;
                                font-weight:700;
                                margin-top:4px;
                            ">
                                ${cam.fov || 90}°
                            </div>

                        </div>

                    </div>

                </div>
            `;

            grid.appendChild(card);

            // =========================================
            // START STREAM ONLY IF ACTIVE
            // =========================================

            if (isActive) {

                startWebSocket(cam.id);

            } else {

                const overlay =
                    document.getElementById(
                        `offlineOverlay${cam.id}`
                    );

                if (overlay) {
                    overlay.style.display = "flex";
                }
            }

        });

    }

    catch(err) {

        console.error(err);

        grid.innerHTML = `
            <div style="
                color:red;
                padding:20px;
                font-size:18px;
            ">
                Failed to load cameras
            </div>
        `;
    }
}


// ======================================================
// START WEBSOCKET
// ======================================================

function startWebSocket(camId) {

    const canvas =
        document.getElementById(`cam${camId}`);

    if (!canvas) {
        return;
    }

    const ctx =
        canvas.getContext("2d");

    const overlay =
        document.getElementById(
            `offlineOverlay${camId}`
        );

    const existing =
        sockets[camId];

    // Prevent duplicate sockets
    if (
        existing &&
        existing.ws &&
        existing.ws.readyState === WebSocket.OPEN
    ) {
        return;
    }

    // Close old socket
    if (existing) {

        try {
            existing.ws.close();
        }
        catch {}
    }

    // Create websocket
    const ws =
        new WebSocket(
            `ws://${location.host}/ws/${camId}`
        );

    sockets[camId] = {ws, canvas};

    let lastFrameTime = Date.now();

    ws.onopen = () => {

        console.log(
            `WS CONNECTED CAM ${camId}`
        );

        if (overlay) {
            overlay.style.display = "none";
        }
    };

    ws.onmessage = function(event) {

        lastFrameTime = Date.now();

        const img = new Image();

        img.src =
            "data:image/jpeg;base64," +
            event.data;

        img.onload = function() {

            ctx.clearRect(
                0,
                0,
                canvas.width,
                canvas.height
            );

            ctx.drawImage(
                img,
                0,
                0,
                canvas.width,
                canvas.height
            );

            if (overlay) {
                overlay.style.display = "none";
            }
        };

        img.onerror = () => {

            if (overlay) {
                overlay.style.display = "flex";
            }
        };
    };

    ws.onerror = err => {

        console.error(
            `WS ERROR CAM ${camId}`,
            err
        );

        if (overlay) {
            overlay.style.display = "flex";
        }
    };

    ws.onclose = () => {

        console.log(
            `WS CLOSED CAM ${camId}`
        );

        if (overlay) {
            overlay.style.display = "flex";
        }

        delete sockets[camId];

        // AUTO RECONNECT
        setTimeout(() => {

            const liveView =
                document.getElementById("live");

            if (
                liveView &&
                liveView.style.display !== "none"
            ) {

                startWebSocket(camId);
            }

        }, 3000);
    };

    // DEAD STREAM DETECTION
    setInterval(() => {

        const now = Date.now();

        if (
            now - lastFrameTime > 5000
        ) {

            if (overlay) {
                overlay.style.display = "flex";
            }
        }

    }, 3000);
}

// ======================================================
// LOAD CAMERA LIST
// ======================================================

async function loadCameraList() {

    camTable.innerHTML =
        "<tr><td colspan='7'>Loading...</td></tr>";

    try {

        const response =
            await fetch("/cameras");

        const cameras =
            await response.json();

        camTable.innerHTML = "";

        cameras.forEach(cam => {

            const row =
                document.createElement("tr");

            row.innerHTML = `

                <td>${cam.description || cam.name}</td>

                <td>${cam.id}</td>

                <td>${cam.ip || ""}</td>

                <td>${cam.username || ""}</td>

                <td>
                    ${cam.network?.mac_address || ""}
                </td>

                <td>
                    ${cam.coverage?.range_meters || 150}m
                </td>

                <td>

                    <button
                        onclick="deleteCamera(${cam.id})"
                    >
                        Delete
                    </button>

                </td>
            `;

            camTable.appendChild(row);

        });

    }

    catch(err) {

        console.error(err);

        camTable.innerHTML =
            "<tr><td colspan='7'>Failed loading cameras</td></tr>";
    }
}


// ======================================================
// ADD CAMERA
// ======================================================

async function addCamera() {

    const button =
        document.querySelector(
            '#addForm button'
        );

    if (button) {

        button.disabled = true;

        button.innerText =
            "Adding...";
    }

    const payload = {

        ip:
            document.getElementById("ip")?.value || "",

        username:
            document.getElementById("user")?.value || "",

        password:
            document.getElementById("password")?.value || "",

        name:
            document.getElementById("name")?.value || "",

        description:
            document.getElementById("description")?.value || "",

        rtsp_url:
            document.getElementById("rtsp")?.value || "",

        network: {

            mac_address:
                document.getElementById("mac")?.value || "",

            assignment: "static",

            dhcp_reserved: false
        },

        position: {

            latitude:
                parseFloat(
                    document.getElementById("latitude")?.value
                ) || 0,

            longitude:
                parseFloat(
                    document.getElementById("longitude")?.value
                ) || 0,

            altitude:
                parseFloat(
                    document.getElementById("altitude")?.value
                ) || 0
        },

        orientation: {

            pan:
                parseFloat(
                    document.getElementById("pan")?.value
                ) || 0,

            tilt:
                parseFloat(
                    document.getElementById("tilt")?.value
                ) || 0,

            zoom:
                parseFloat(
                    document.getElementById("zoom")?.value
                ) || 1
        },

        fov:
            parseFloat(
                document.getElementById("fov")?.value
            ) || 90,

        coverage: {

            range_meters:
                parseFloat(
                    document.getElementById("range_meters")?.value
                ) || 150,

            max_range: 150,

            fov_angle: 90,

            vertical_fov: 60,

            bearing_start: 0,

            bearing_end: 90,

            pan_min: 0,

            pan_max: 360
        }
    };

    try {

        // 15 second timeout
        const controller =
            new AbortController();

        const timeout =
            setTimeout(() => {

                controller.abort();

            }, 15000);

        const response =
            await fetch("/add_camera", {

                method: "POST",

                headers: {
                    "Content-Type":
                    "application/json"
                },

                body:
                    JSON.stringify(payload),

                signal:
                    controller.signal
            });

        clearTimeout(timeout);

        const data =
            await response.json();

        console.log(data);

        alert(
            "Camera added successfully"
        );

        await loadCameraList();

        await loadLiveCameras();

    }

    catch(err) {

        console.error(err);

        if (
            err.name === "AbortError"
        ) {

            alert(
                "Camera add timeout"
            );

        } else {

            alert(
                "Failed to add camera"
            );
        }
    }

    finally {

        if (button) {

            button.disabled = false;

            button.innerText =
                "Add Camera";
        }
    }
}


// ======================================================
// DELETE CAMERA
// ======================================================

async function deleteCamera(id) {

    await fetch("/delete_camera", {

        method: "POST",

        headers: {
            "Content-Type":
            "application/json"
        },

        body:
            JSON.stringify({id})
    });

    loadCameraList();

    loadLiveCameras();
}


// ======================================================
// DISCOVER CAMERAS
// ======================================================

async function discoverCameras() {

    try {

        const response =
            await fetch("/discover_cameras", {

                method: "POST"
            });

        const data =
            await response.json();

        console.log(
            "Discovery response:",
            data
        );

        await loadCameraList();

        await loadLiveCameras();

        alert(
            `${data.count || 0} cameras discovered`
        );

    }

    catch(err) {

        console.error(err);

        alert("Discovery failed");
    }
}


// ======================================================
// MAP POINT CAMERA SELECTION
// ======================================================

async function selectCameraForPoint() {

    const lat =
        parseFloat(
            document.getElementById(
                "targetLatitude"
            ).value
        );

    const lon =
        parseFloat(
            document.getElementById(
                "targetLongitude"
            ).value
        );

    const output =
        document.getElementById(
            "pointResult"
        );

    try {

        const response =
            await fetch("/point", {

                method: "POST",

                headers: {
                    "Content-Type":
                    "application/json"
                },

                body:
                    JSON.stringify({

                        latitude: lat,

                        longitude: lon
                    })
            });

        const data =
            await response.json();

        output.innerText =
            JSON.stringify(data, null, 2);

    }

    catch(err) {

        output.innerText =
            "Point selection failed";
    }
}


// ======================================================
// ANALYTICS
// ======================================================

function showAnalytics() {

    hideAll();

    const el =
        document.getElementById(
            "analytics"
        );

    if (el) {

        el.style.display = "block";
    }
}


async function updateCameraStatus() {

    try {

        const response =
            await fetch("/camera-health");

        const health =
            await response.json();

        const activeIds =
            new Set(
                (health.active_cameras || [])
                .map(c => c.camera_id)
            );

        document
            .querySelectorAll(".camera")
            .forEach(card => {

                const camId =
                    parseInt(card.dataset.id);

                if (activeIds.has(camId)) {

                    card.style.border =
                        "3px solid #00ff66";

                } else {

                    card.style.border =
                        "3px solid red";
                }
            });

    }

    catch(err) {

        console.error(err);
    }
}

showLive();

setInterval(updateCameraStatus, 5000);