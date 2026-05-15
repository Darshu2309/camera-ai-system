from fastapi import APIRouter

from pydantic import BaseModel

from commands.parser import parse_command

from commands.validator import validate_command

from commands.dispatcher import dispatch_command


router = APIRouter()


# =====================================================
# REQUEST MODEL
# =====================================================

class CommandRequest(BaseModel):

    command: str


# =====================================================
# COMMAND API
# =====================================================

@router.post("/command")
async def command_api(req: CommandRequest):

    try:

        # -----------------------------------------
        # IMPORT CAMERAS
        # -----------------------------------------

        from main import cameras

        # -----------------------------------------
        # PARSE COMMAND
        # -----------------------------------------

        parsed = parse_command(

            req.command
        )

        # -----------------------------------------
        # VALIDATE
        # -----------------------------------------

        validate_command(

            parsed,
            cameras
        )

        # -----------------------------------------
        # DISPATCH
        # -----------------------------------------

        result = dispatch_command(

            parsed,
            cameras
        )

        # -----------------------------------------
        # RESPONSE
        # -----------------------------------------

        return {

            "status": "success",

            "parsed_command": {

                "action": parsed.action,

                "camera_id": parsed.camera_id,

                "direction": getattr(
                    parsed,
                    "direction",
                    None
                ),

                "angle": getattr(
                    parsed,
                    "angle",
                    None
                ),

                "zoom": getattr(
                    parsed,
                    "zoom",
                    None
                ),

                "target": getattr(
                    parsed,
                    "target",
                    None
                )
            },

            "result": result
        }

    except Exception as e:

        return {

            "status": "error",

            "message": str(e)
        }