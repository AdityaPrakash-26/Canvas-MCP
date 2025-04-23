from mcp.server.fastmcp import Context, FastMCP
from datetime import datetime
def register_grade_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_course_grade(ctx: Context, course_id: int) -> dict[str, any]:
        """
        Retrieves the student's current grade from Canvas for the given course.
        """
        api = ctx.request_context.lifespan_context["api_adapter"]
        db = ctx.request_context.lifespan_context["db_manager"]
        # Map local course ID to Canvas ID
        row = db.get_by_id("courses", course_id)
        if not row:
            return {"error": f"Course {course_id} not found"}

        enrollment = api.get_user_enrollment_raw(row["canvas_course_id"])
        if not enrollment:
            return {"unavailable": True, "reason": "no enrollment"}

        score = getattr(enrollment, "computed_current_score", None)
        letter = getattr(enrollment, "computed_current_grade", None)

        if score is None and letter is None:
            return {"unavailable": True}

        return {
            "course_code": row["course_code"],
            "course_name": row["course_name"],
            "current_score": score,
            "current_grade": letter,
            "as_of": datetime.utcnow().isoformat() + "Z",
        }