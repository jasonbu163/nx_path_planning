from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from .response import StandardResponse

async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 FastAPI 的 HTTPException"""
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardResponse.isError(
            message=exc.detail,
            code=exc.status_code,
            status="error"
        ).model_dump()  # 使用 model_dump() 代替 .dict()
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    return JSONResponse(
        status_code=500,
        content=StandardResponse.isError(
            message="服务器内部错误",
            code=500,
            status="internal_server_error",
            data={"detail": str(exc)}
        ).model_dump()
    )