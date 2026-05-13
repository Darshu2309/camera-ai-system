from fastapi import APIRouter
from fastapi import HTTPException
import json

with open("cameras.json") as f:
    cameras = json.load(f)
    
from models.point_models import PointRequest

from services.camera_selector import (
    select_best_camera,
    calculate_ptz
)

router = APIRouter()


@router.post("/point")
async def point_api(data: PointRequest):

    try:

        target = {

            "latitude": data.latitude,

            "longitude": data.longitude
        }

        if not cameras:

            raise HTTPException(
                status_code=400,
                detail="No cameras available"
            )

        selected_cam = select_best_camera(
            cameras,
            target
        )

        if not selected_cam:

            raise HTTPException(
                status_code=404,
                detail="No suitable camera found"
            )

        ptz = calculate_ptz(
            selected_cam,
            target
        )

        print(f"""

=============================
GIS CAMERA ORCHESTRATION
=============================

Selected Camera:
{selected_cam['id']}

Target:
{target}

Pan:
{ptz['pan']}

Tilt:
{ptz['tilt']}

=============================

""")

        return {

            "status": "camera_selected",

            "camera_id":
            selected_cam["id"],

            "camera_name":
            selected_cam.get("name"),

            "stream_url":
            selected_cam.get(
                "stream_url"
            ),

            "ptz": ptz,

            "target": target
        }

    except Exception as e:

        print("[POINT API ERROR]", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )