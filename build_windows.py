"""
Windows 打包脚本
使用 PyInstaller 将缠论分析器打包成 Windows 可执行文件

使用方法:
    1. 安装 PyInstaller: pip install pyinstaller
    2. 在 Windows 上运行此脚本: python build_windows.py

注意: 必须在 Windows 系统上运行才能生成 .exe 文件
"""
import subprocess
import sys
import os
from pathlib import Path

def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        import PyInstaller
        print(f"✓ PyInstaller 已安装 (版本: {PyInstaller.__version__})")
        return True
    except ImportError:
        print("✗ PyInstaller 未安装")
        print("  请运行: pip install pyinstaller")
        return False

def build():
    """执行打包"""
    if not check_pyinstaller():
        sys.exit(1)

    # 项目路径
    project_root = Path(__file__).parent
    app_dir = project_root / "App"
    main_script = app_dir / "chan_app.py"

    if not main_script.exists():
        print(f"✗ 找不到入口文件: {main_script}")
        sys.exit(1)

    print(f"\n开始打包: {main_script}")
    print("=" * 50)

    # PyInstaller 参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=缠论分析器",           # 程序名称
        "--onefile",                    # 打包成单个exe文件
        "--windowed",                   # 不显示控制台窗口
        "--noconfirm",                  # 覆盖已有文件
        "--clean",                      # 清理临时文件

        # 添加数据文件（股票列表）
        f"--add-data={app_dir / 'stock_list.csv'};App",

        # 添加隐式导入（防止打包遗漏）
        "--hidden-import=akshare",
        "--hidden-import=baostock",
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--hidden-import=matplotlib",
        "--hidden-import=matplotlib.backends.backend_tkagg",

        # 路径设置
        f"--paths={project_root}",
        f"--specpath={project_root / 'build'}",
        f"--distpath={project_root / 'dist'}",
        f"--workpath={project_root / 'build' / 'temp'}",

        # 入口文件
        str(main_script),
    ]

    print("执行命令:")
    print(" ".join(cmd))
    print()

    # 执行打包
    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode == 0:
        exe_path = project_root / "dist" / "缠论分析器.exe"
        print("\n" + "=" * 50)
        print("✓ 打包成功!")
        print(f"  输出文件: {exe_path}")
        print("\n使用说明:")
        print("  1. 将 dist/缠论分析器.exe 复制到任意位置")
        print("  2. 双击运行即可")
    else:
        print("\n✗ 打包失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    build()
