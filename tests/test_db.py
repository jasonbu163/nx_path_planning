# tests/test_db.py
from sys_path import setup_path
setup_path()

from app.models import init_db, init_locations
from app.models.base_model import LocationList, OrderList, TaskList
from app.models.base_enum import LocationStatus, OrderType, TaskStatus, TaskType

def test_db():
    print(LocationStatus.FREE.value)
    mode = LocationList()
    print(mode.__repr__())
def main():
    # init_db()
    init_locations()
    # test_db()

if __name__ == '__main__':
    main()