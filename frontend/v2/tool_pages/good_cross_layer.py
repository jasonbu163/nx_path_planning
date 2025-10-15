good_switch_pages = {
        "📦 货物跨层": [
        {
            "title": "步骤 1：启动PLC确认，小车去放料",
            "api":"/control/task_in_lift",
            "method": "POST",
            "params": {"location_id": 1}
        },
        {
            "title": "步骤 2：操作小车放货",
            "api": "/control/good_move_segments",
            "method": "POST",
            "params": {
                "source": "1,1,1",
                "target": "6,3,1",
                "points": ["1,1,1", "3,2,1", "6,3,1"]
            }
        },
        {
            "title": "步骤 3：确认在对应楼层，小车放料完成✅",
            "api":  "/control/task_feed_complete",
            "method": "POST",
            "params": {"location_id": 1}
        },
        {
            "title": "步骤 4：电梯移动",
            "api": "/control/lift",
            "method": "POST",
            "params": {"location_id": 1}
        },
        {
            "title": "步骤 5：提升机物料 ➡️ 库内",
            "api": "/control/task_out_lift",
            "method": "POST",
            "params": {
                "location_id": 1
            }
        },
        {
            "title": "步骤 5：操作小车取货",
            "api": "/control/good_move_segments",
            "method": "POST",
            "params": {
                "source": "1,1,1",
                "target": "6,3,1",
                "points": ["1,1,1", "3,2,1", "6,3,1"]
            }
        },
        {
            "title": "步骤 6：入库完成确认",
            "api": "/control/task_pick_complete",
            "method": "POST",
            "params": {
                "location_id": 1
            }
        }
    ]
}