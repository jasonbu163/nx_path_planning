# app/api/v2/wcs/advance_route.py
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.api.v2.core.dependencies import get_database
from app.core.config import settings
from . import schemas
from .advance_function import AdvanceFunction

router = APIRouter(prefix="/path_test", tags=["路径规划测试"])
service = AdvanceFunction()


@router.post("/get_block_node")
async def get_block_node(
    request: schemas.GoodMoveBase,
    db: Session = get_database()
):
    """查询路径是否存在障碍"""
    success, result = service.get_block_node(
        request.start_location,
        request.end_location,
        db
    )
    return {
        "success": success,
        "result": result
    }

@router.post("/find_block_node_nearest_highway")
async def find_block_node_nearest_highway(
    request: schemas.GoodMoveBase,
    db: Session = get_database()
):
    """查询路径是否存在障碍"""
    success, result = service.find_block_node_nearest_highway(
        request.start_location,
        request.end_location,
        db
    )
    return {
        "success": success,
        "result": result
    }

@router.post("/find_free_nodes_excluding_path")
async def find_free_nodes_excluding_path(
    request: schemas.GoodMoveBase,
    db: Session = get_database()
):
    """查询路径是否存在障碍"""
    success, result = service.find_free_nodes_excluding_path(
        request.start_location,
        request.end_location,
        db
    )
    return {
        "success": success,
        "result": result
    }

@router.post("/find_nearest_free_node")
async def find_nearest_free_node(
    request: schemas.MovePoint,
    db: Session = get_database()
):
    """查询路径障碍点可移动最近位置"""
    success, result = service.find_nearest_free_node(
        request.start_location,
        request.end_location,
        request.move_point,
        db
    )
    return {
        "success": success,
        "result": result
    }

@router.post("/find_farthest_free_node")
async def find_farthest_free_node(
    request: schemas.MovePoint,
    db: Session = get_database()
):
    """查询路径障碍点可移动最远位置"""
    success, result = service.find_farthest_free_node(
        request.start_location,
        request.end_location,
        request.move_point,
        db
    )
    return {
        "success": success,
        "result": result
    }