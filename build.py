# build.py
import os
import shutil
import subprocess

def clean_build_folders():
    """清理构建文件夹"""
    folders_to_clean = ['build', 'dist']
    for folder in folders_to_clean:
        if os.path.exists(folder):
            print(f"清理 {folder} 文件夹...")
            shutil.rmtree(folder)

def copy_resources():
    """复制必要的资源文件到dist文件夹"""
    # 确保dist文件夹存在
    if not os.path.exists('dist/nx_path_planning'):
        return
    
    # 复制配置文件夹
    if os.path.exists('app/data'):
        print("复制配置文件夹...")
        shutil.copytree('app/data', 'dist/nx_path_planning/app/data', dirs_exist_ok=True)
        shutil.copytree('app/map_core/data', 'dist/nx_path_planning/app/map_core/data', dirs_exist_ok=True)

def build_executable():
    """使用PyInstaller构建可执行文件"""
    print("开始构建可执行文件...")
    
    # PyInstaller命令行参数
    pyinstaller_args = [
        'pyinstaller',
        '--name=nx_scb_wcs',
        '--noconfirm',  # 覆盖输出目录
        '--add-data=app/data;app/data',  # 添加配置文件夹
        '--add-data=app/map_core/data;app/map_core/data',
        '--icon=ui/icon.ico' if os.path.exists('ui/img/icon.ico') else '',  # 如果存在图标则添加
        'run.py'  # 主程序入口
    ]
    
    # 过滤掉空参数
    pyinstaller_args = [arg for arg in pyinstaller_args if arg]
    
    # 执行PyInstaller命令
    try:
        subprocess.run(pyinstaller_args, check=True)
        print("构建成功!")
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        return False
    
    return True

def main():
    # 确保当前工作目录是项目根目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("=== 开始打包 nx_scb_wcs 应用 ===")
    
    # 清理旧的构建文件
    clean_build_folders()
    
    # 构建可执行文件
    if build_executable():
        # 复制额外资源
        copy_resources()
        print("\n打包完成! 可执行文件位于 dist/nx_scb_wcs 文件夹")
    else:
        print("\n打包失败!")

if __name__ == "__main__":
    main()