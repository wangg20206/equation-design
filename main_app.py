# main_app.py

import sys
import threading
import uvicorn
from api_service import app as fastapi_app # 呼叫副程式 api_service.py
from gui_client import MainWindow, QApplication # 呼叫副程式 gui_client.py

# --- FastAPI 啟動函式 ---
def start_fastapi_server():
    """
    使用 uvicorn 啟動 FastAPI 服務 (在獨立執行緒中運行)
    """
    try:
        # log_level="error" 減少終端機輸出，只顯示錯誤
        uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="error") 
    except Exception as e:
        print(f"FastAPI Server failed to start: {e}")

# --- 主程式啟動點 (if __name__ == '__main__':) ---
if __name__ == '__main__':
    # 1. 啟動 FastAPI 服務執行緒
    server_thread = threading.Thread(target=start_fastapi_server, daemon=True)
    server_thread.start()
    print("--- FastAPI Server (Thread) started on http://127.0.0.1:8000 ---")
    
    # 2. 啟動 PyQt5 應用程式 (必須在主執行緒中運行)
    print("--- Starting PyQt5 Client ---")
    qt_app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # 3. 執行 PyQt5 應用程式的主迴圈
    sys.exit(qt_app.exec_())