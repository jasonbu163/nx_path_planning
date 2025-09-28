# tests/test_db.py
from sys_path import setup_path
setup_path()

from app.models import init_db, init_locations

def main():
    # init_db()
    init_locations()

if __name__ == '__main__':
    main()