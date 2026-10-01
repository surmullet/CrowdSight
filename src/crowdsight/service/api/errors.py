"""RFC 9457 Problem Details (application/problem+json) error handling."""
from __future__ import annotations

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


class ProblemDetails(BaseModel):
    """RFC 9457 compliant error response."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = Field(
        default="about:blank",
        description="URI reference that identifies the problem type.",
    )
    title: str = Field(description="Short, human-readable summary of the problem type.")
    status: int = Field(description="The HTTP status code.")
    detail: str = Field(description="Human-readable explanation specific to this occurrence of the problem.")
    instance: str | None = Field(
        default=None,
        description="URI reference that identifies the specific occurrence of the problem.",
    )
    code: str = Field(
        description="Stable machine-readable error code.",
    )
    user_action_hint: str | None = Field(
        default=None,
        description="Actionable advice for the user/operator to resolve or report the issue.",
    )


class APIProblemException(HTTPException):
    """Exception carrying RFC 9457 problem details."""

    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        code: str,
        user_action_hint: str | None = None,
        problem_type: str = "about:blank",
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.problem = ProblemDetails(
            type=problem_type,
            title=title,
            status=status_code,
            detail=detail,
            code=code,
            user_action_hint=user_action_hint,
        )


def problem_response(
    status_code: int,
    title: str,
    detail: str,
    code: str,
    request: Request,
    user_action_hint: str | None = None,
    problem_type: str = "about:blank",
) -> Response:
    """Build an application/problem+json response."""
    problem = ProblemDetails(
        type=problem_type,
        title=title,
        status=status_code,
        detail=detail,
        instance=request.url.path,
        code=code,
        user_action_hint=user_action_hint,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(mode="json", exclude_none=True),
        media_type="application/problem+json",
    )
