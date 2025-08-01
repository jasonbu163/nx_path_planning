from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional
from enum import Enum

T = TypeVar("T") # 通用类型变量

# 定义响应含义和状态码
class StatusCode(Enum):
    SUCCESS = (True, 200, "ok")
    BAD_REQUEST = (False, 400, "bad_request")
    UNAUTHORIZED = (False, 401, "unauthorized")
    FORBIDDEN = (False, 403, "forbidden")
    NOT_FOUND = (False, 404, "not_found")
    CONFLICT = (False, 409, "conflict")
    INTERNAL_ERROR = (False, 500, "internal_server_error")
    
    def __init__(self, boolean, code, status):
        self.boolean = boolean
        self.code = code
        self.status = status

# api响应类
class StandardResponse(BaseModel, Generic[T]):
    success: bool
    code: int
    status: str
    message: str
    data: Optional[T] = None

    @classmethod
    def isSuccess(
        cls,
        data: Optional[T] = None,
        message: str = "操作成功",
        success: bool = StatusCode.SUCCESS.boolean,
        code: int = StatusCode.SUCCESS.code,
        status: str = StatusCode.SUCCESS.status
        ):
        """成功响应快捷方法"""
        return cls(
            success=success,
            code=code,
            status=status,
            message=message,
            data=data
            )
    
    @classmethod
    def isError(
        cls,
        data: Optional[T] = None,
        message: str = "",
        success: bool = StatusCode.NOT_FOUND.boolean,
        code: int = StatusCode.NOT_FOUND.code,
        status: str = StatusCode.NOT_FOUND.status
        ):
        """失败响应快捷方法"""
        return cls(
            success=success,
            code=code,
            status=status,
            message=message,
            data=data
            )