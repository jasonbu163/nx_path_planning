# build.py
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

def download_snap7_dll():
    """下载 snap7.dll 文件"""
    print("正在下载 snap7.dll...")
    snap7_url = "https://sourceforge.net/projects/snap7/files/1.4.2/snap7-full-1.4.2.7z/download"
    download_path = "snap7-full-1.4.2.7z"
    extract_dir = "snap7_temp"
    
    try:
        # 下载 snap7
        urllib.request.urlretrieve(snap7_url, download_path)
        print("下载完成")
        
        # 解压文件
        with zipfile.ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print("解压完成")
        
        # 查找并复制 snap7.dll
        for root, dirs, files in os.walk(extract_dir):
            if "snap7.dll" in files:
                dll_path = os.path.join(root, "snap7.dll")
                shutil.copy2(dll_path, "snap7.dll")
                print(f"找到并复制 snap7.dll: {dll_path}")
                break
        
        # 清理临时文件
        shutil.rmtree(extract_dir)
        os.remove(download_path)
        
        return True
    except Exception as e:
        print(f"下载 snap7.dll 失败: {e}")
        return False
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
    dist_path = 'dist/nx_path_planning'
    if not os.path.exists(dist_path):
        return
    
    # 复制配置文件夹
    if os.path.exists('app/data'):
        print("复制配置文件夹...")
        shutil.copytree('app/data', 'dist/nx_path_planning/app/data', dirs_exist_ok=True)
    
    if os.path.exists('app/map_core/data'):
        shutil.copytree('app/map_core/data', 'dist/nx_path_planning/app/map_core/data', dirs_exist_ok=True)

    # 复制 snap7.dll
    if os.path.exists('snap7.dll'):
        print("复制 snap7.dll...")
        shutil.copy2('snap7.dll', dist_path)

def build_executable():
    """使用PyInstaller构建可执行文件"""
    print("开始构建可执行文件...")
    
    # PyInstaller命令行参数
    pyinstaller_args = [
        'pyinstaller',
        '--name=nx_path_planning',
        '--noconfirm',  # 覆盖输出目录
        '--add-data=app/data;app/data',  # 添加配置文件夹
        '--add-data=app/map_core/data;app/map_core/data',
        '--hidden-import=snap7'
    ]

    # 添加图标如果存在
    if os.path.exists('ui/img/icon.ico'):
        pyinstaller_args.append('--icon=ui/img/icon.ico')

    # 添加 snap7.dll 如果存在
    if os.path.exists('snap7.dll'):
        pyinstaller_args.append('--add-binary=snap7.dll;.')

    # 添加主程序入口
    pyinstaller_args.append('run.py')

    # 过滤掉空参数
    # pyinstaller_args = [arg for arg in pyinstaller_args if arg]
    
    # 执行PyInstaller命令
    try:
        print(f"执行命令: {' '.join(pyinstaller_args)}")
        subprocess.run(pyinstaller_args, check=True)
        print("构建成功!")
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        return False
    
    return True

def main():
    # 确保当前工作目录是项目根目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("=== 开始打包 nx_path_planning 应用 ===")

    # 检查并下载 snap7.dll
    if not os.path.exists('snap7.dll'):
        if not download_snap7_dll():
            print("无法获取 snap7.dll，请手动下载并放置在项目根目录")
            print("下载地址: https://sourceforge.net/projects/snap7/files/")
            return
    
    # 清理旧的构建文件
    clean_build_folders()
    
    # 构建可执行文件
    if build_executable():
        # 复制额外资源
        copy_resources()
        print("\n打包完成! 可执行文件位于 dist/nx_path_planning 文件夹")
    else:
        print("\n打包失败!")

if __name__ == "__main__":
    main()