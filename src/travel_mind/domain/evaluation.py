from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(BaseModel):
    code: str = Field(description="问题代码")
    severity: IssueSeverity = Field(description="问题严重程度")
    message: str = Field(description="问题说明")
    day: date | None = Field(default=None, description="问题所在日期")


class ValidationReport(BaseModel):
    """校验报告"""

    passed: bool = Field(description="是否通过确定性校验")
    issues: list[ValidationIssue] = Field(
        default_factory=list, description="发现的问题"
    )
