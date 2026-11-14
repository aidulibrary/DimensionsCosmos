import sys, runpy, pathlib
TARGET = r'D:\DimensionsCosmos\pipeline\pinyin\build_pinyin.py'
sys.argv = [TARGET] + sys.argv[1:]
runpy.run_path(TARGET, run_name='__main__')
