@echo off
:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 执行 bot.py 文件
python bot.py

:: 可选：在程序结束后暂停，以便查看日志
pause
