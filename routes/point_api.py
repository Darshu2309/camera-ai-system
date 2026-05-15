from fastapi import APIRouter
from fastapi import HTTPException

from models.point_models import PointRequest

from services.camera_selector import (
    describe_camera_coverage,
    select_best_camera,
    calculate_ptz
)
from services.visibility_engine import evaluate_visibility
from services.guidance_service import build_operator_guidance

router = APIRouter()


@router.post("/point")
async def point_api(data: PointRequest):

    try:
        from main import cameras

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
            selected_cam.get("description") or selected_cam.get("name"),

            "camera_description":
            selected_cam.get("description") or selected_cam.get("name"),

            "stream_url":
            selected_cam.get(
                "stream_url"
            ),

            "ptz": ptz,

            "coverage":
            describe_camera_coverage(selected_cam),

            "visibility":
            evaluate_visibility(selected_cam, target),

            "operator_guidance":
            build_operator_guidance(
                event_type="camera_selected",
                location=f"{target['latitude']:.8f}, {target['longitude']:.8f}",
                camera=selected_cam.get("description") or selected_cam.get("name"),
                language="hi",
            ),

            "target": target
        }

    except HTTPException:
        raise

    except Exception as e:

        print("[POINT API ERROR]", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
