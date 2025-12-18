# gui_client.py

import sys
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QTextEdit,
    QDialog, QGridLayout, QComboBox
)
from matplotlib.ticker import MultipleLocator

import matplotlib.pyplot as plt 
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS'] 
plt.rcParams['axes.unicode_minus'] = False
from PyQt5.QtCore import Qt

# --- 設定後端 API 基本路徑 ---
API_BASE_URL = "http://127.0.0.1:8000"

# ----------------------------------------
# A. 新增/編輯書籍的 QDialog 彈出視窗
# ----------------------------------------
class BookFormDialogV2(QDialog):
    def __init__(self, parent=None, book_data=None):
        super().__init__(parent)
        self.setWindowTitle("新增/編輯書籍資料")
        self.book_data = book_data 
        self.is_edit_mode = book_data is not None
        self.setGeometry(200, 200, 400, 300)
        
        main_layout = QGridLayout(self)
        self.fields = {
            "title": ("書名:", QLineEdit()),
            "author": ("作者:", QLineEdit()),
            "isbn": ("ISBN:", QLineEdit()),
            "category": ("類別:", QComboBox()),
            "url": ("網址:", QLineEdit()),
        }
        categories = ["文學", "科學", "歷史", "藝術", "其他"]
        self.fields["category"][1].addItems(categories)
        
        row = 0
        for key, (label_text, widget) in self.fields.items():
            main_layout.addWidget(QLabel(label_text), row, 0)
            main_layout.addWidget(widget, row, 1)
            row += 1

        if self.is_edit_mode:
            self.setWindowTitle("編輯書籍資料")
            self.fields['isbn'][1].setReadOnly(True)
            for key, (_, widget) in self.fields.items():
                if self.book_data and key in self.book_data:
                    value = self.book_data[key] if self.book_data[key] is not None else ""
                    if isinstance(widget, QLineEdit):
                        widget.setText(value)
                    elif isinstance(widget, QComboBox):
                        index = widget.findText(value)
                        if index != -1:
                            widget.setCurrentIndex(index)

        self.save_button = QPushButton("💾 儲存")
        self.save_button.clicked.connect(self.accept) 
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout, row, 0, 1, 2)

    def get_book_data(self):
        data = {}
        for key, (_, widget) in self.fields.items():
            if isinstance(widget, QLineEdit):
                data[key] = widget.text().strip()
            elif isinstance(widget, QComboBox):
                data[key] = widget.currentText()
                
        for key, value in data.items():
            if not value and key != 'isbn':
                 data[key] = None
        return data


# ----------------------------------------
# B. Matplotlib 圖表顯示視窗
# ----------------------------------------
class StatChartDialog(QDialog):
    def __init__(self, parent=None, stats_data=None):
        super().__init__(parent)
        self.setWindowTitle("📚 書籍類別統計圖表")
        self.setGeometry(300, 300, 600, 500)
        self.stats_data = stats_data
        
        layout = QVBoxLayout(self)
        
        # 建立 Matplotlib 畫布
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.draw_chart()

    def draw_chart(self):
        """繪製柱狀圖"""
        if not self.stats_data:
            self.ax.text(0.5, 0.5, "No statistical data", ha='center', va='center')
            self.canvas.draw()
            return
            
        categories = list(self.stats_data.keys())
        counts = list(self.stats_data.values())
        self.ax.clear()
        self.ax.bar(categories, counts, color='skyblue') 
        self.ax.set_title("Book Categories by Quantity")
        self.ax.set_xlabel("Categories")
        self.ax.set_ylabel("Quantity")
        y_major_locator = MultipleLocator(1.00)
        self.ax.yaxis.set_major_locator(y_major_locator) # 目的：將 Y 軸刻度間隔設定為 1.0，只顯示整數 (0, 1, 2...)
        self.ax.tick_params(axis='x', rotation=45) # 標籤旋轉
        self.figure.tight_layout()
        self.canvas.draw()


# ----------------------------------------
# C. 主視窗 (MainWindow)
# ----------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📚 虛擬圖書管理系統 (PyQt5 Client)")
        self.setGeometry(100, 100, 800, 600)
        self.current_book_data = None # 用於儲存當前查詢到的書籍資料

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # A. 查詢區域
        query_group = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("輸入書籍 ISBN (國際標準書號) 進行查詢 (9786267098943 , 978-0321765723)")
        self.query_button = QPushButton("🔍 查詢")
        self.query_button.clicked.connect(self.query_book_by_isbn)
        query_group.addWidget(self.query_input)
        query_group.addWidget(self.query_button)

        # B. 結果顯示區域
        self.result_text_edit = QTextEdit()
        self.result_text_edit.setReadOnly(True) 
        self.result_text_edit.setMinimumHeight(150)

        # C. 功能按鈕區域
        button_group = QHBoxLayout()
        
        self.add_button = QPushButton("➕ 新增書籍")
        self.add_button.clicked.connect(self.show_add_dialog)
        
        self.update_button = QPushButton("✏️ 更新書籍")
        self.update_button.clicked.connect(self.show_update_dialog)
        self.update_button.setEnabled(False) 
        
        self.delete_button = QPushButton("🗑️ 刪除書籍")
        self.delete_button.clicked.connect(self.delete_book_confirmation)
        self.delete_button.setEnabled(False)
        
        self.stats_button = QPushButton("📊 統計圖表")
        self.stats_button.clicked.connect(self.show_stats_chart)
        self.stats_button.setEnabled(True) 

        button_group.addWidget(self.add_button)
        button_group.addWidget(self.update_button)
        button_group.addWidget(self.delete_button)
        button_group.addStretch(1)
        button_group.addWidget(self.stats_button)

        # D. 組合佈局
        main_layout.addLayout(query_group)
        main_layout.addWidget(QLabel("查詢結果："))
        main_layout.addWidget(self.result_text_edit)
        main_layout.addLayout(button_group)
        main_layout.addStretch(1)


    # --- 錯誤處理輔助函數 ---
    def handle_api_error(self, response):
        QMessageBox.critical(self, "API 錯誤", f"操作失敗，狀態碼: {response.status_code}\n訊息: {response.text}")

    def handle_connection_error(self):
        QMessageBox.critical(self, "連線錯誤", f"無法連線到 FastAPI 後端服務：{API_BASE_URL}\n請確認服務已運行。")
    
    # --- CRUD/查詢/統計方法 (詳細程式碼請參考前一個回覆，此處僅列出簽名) ---
    def query_book_by_isbn(self):
        # 實作查詢邏輯 (GET /books/{isbn})
        isbn = self.query_input.text().strip()
        self.result_text_edit.clear()
        self.update_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.current_book_data = None
        if not isbn:
            self.result_text_edit.setText("<font color='red'>請輸入有效的 ISBN 進行查詢。</font>")
            return
        
        try:
            response = requests.get(f"{API_BASE_URL}/books/{isbn}")
            if response.status_code == 200:
                book_data = response.json()
                self.current_book_data = book_data
                self.update_button.setEnabled(True)
                self.delete_button.setEnabled(True)
                
                formatted_text = (
                    f"<h2>✅ 查詢成功</h2>"
                    f"<b>書名：</b> {book_data.get('title')}<br>"
                    f"<b>作者：</b> {book_data.get('author')}<br>"
                    f"<b>ISBN：</b> {book_data.get('isbn')}<br>"
                    f"<b>類別：</b> {book_data.get('category')}<br>"
                    f"<b>網址：</b> <a href='{book_data.get('url')}'>{book_data.get('url')}</a><br>"
                )
                self.result_text_edit.setHtml(formatted_text)
            elif response.status_code == 404:
                self.result_text_edit.setText(f"<font color='orange'><b>🚫 找不到書籍</b></font><br>錯誤：ISBN {isbn} 在資料庫中不存在。")
            else:
                self.handle_api_error(response)
        except requests.exceptions.ConnectionError:
            self.handle_connection_error()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"發生未知錯誤: {e}")

    def show_add_dialog(self):
        # 實作新增邏輯 (POST /books)
        dialog = BookFormDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            book_data = dialog.get_book_data()
            isbn = book_data.get('isbn')
            if not isbn:
                QMessageBox.warning(self, "錯誤", "ISBN 欄位為必填項！")
                return
            try:
                response = requests.post(f"{API_BASE_URL}/books", json=book_data)
                if response.status_code == 201:
                    QMessageBox.information(self, "成功", f"書籍《{book_data['title']}》新增成功！")
                    self.query_input.setText(isbn)
                    self.query_book_by_isbn()
                elif response.status_code == 400:
                    QMessageBox.warning(self, "失敗", f"新增失敗：ISBN {isbn} 已存在。")
                else:
                    self.handle_api_error(response)
            except requests.exceptions.ConnectionError:
                self.handle_connection_error()
    
    def show_update_dialog(self):
        # 實作更新邏輯 (PUT /books/{isbn})
        if not self.current_book_data: return
        dialog = BookFormDialog(self, book_data=self.current_book_data)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_book_data()
            isbn = updated_data.get('isbn')
            try:
                response = requests.put(f"{API_BASE_URL}/books/{isbn}", json=updated_data)
                if response.status_code == 200:
                    QMessageBox.information(self, "成功", f"書籍《{updated_data['title']}》更新成功！")
                    self.query_book_by_isbn()
                else:
                    self.handle_api_error(response)
            except requests.exceptions.ConnectionError:
                self.handle_connection_error()

    def delete_book_confirmation(self):
        # 實作刪除確認與邏輯 (DELETE /books/{isbn})
        if not self.current_book_data: return
        book_title = self.current_book_data.get('title')
        isbn = self.current_book_data.get('isbn')
        reply = QMessageBox.question(
            self, '刪除確認', f"您確定要刪除書籍《<b>{book_title}</b>》嗎？\nISBN: {isbn}", 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                response = requests.delete(f"{API_BASE_URL}/books/{isbn}")
                if response.status_code == 204:
                    QMessageBox.information(self, "成功", f"書籍《{book_title}》已成功刪除！")
                    self.result_text_edit.clear()
                    self.query_input.clear()
                    self.update_button.setEnabled(False)
                    self.delete_button.setEnabled(False)
                    self.current_book_data = None
                else:
                    self.handle_api_error(response)
            except requests.exceptions.ConnectionError:
                self.handle_connection_error()

    def show_stats_chart(self):
        # 實作圖表統計邏輯 (GET /stats)
        try:
            response = requests.get(f"{API_BASE_URL}/stats")
            
            if response.status_code == 200:
                stats_data = response.json()
                if not stats_data:
                    QMessageBox.information(self, "提示", "目前資料庫中沒有書籍，無法顯示統計圖表。")
                    return

                chart_dialog = StatChartDialog(self, stats_data=stats_data)
                chart_dialog.exec_()
            else:
                self.handle_api_error(response)
                
        except requests.exceptions.ConnectionError:
            self.handle_connection_error()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"統計功能發生未知錯誤: {e}")




class BookFormDialog(QDialog):
    def __init__(self, parent=None, book_data=None):
        super().__init__(parent)
        self.setWindowTitle("新增/編輯書籍資料")
        self.book_data = book_data 
        self.is_edit_mode = book_data is not None
        self.setGeometry(200, 200, 500, 350) # 稍微加大視窗寬度
        
        main_layout = QGridLayout(self)
        
        # 定義欄位 (注意：我們將在這裡對 ISBN 做特殊處理)
        self.fields = {
            "title": ("書名:", QLineEdit()),
            "author": ("作者:", QLineEdit()),
            # ISBN 暫時不放在這裡自動生成，因為要加按鈕
            "category": ("類別:", QComboBox()),
            "url": ("網址:", QLineEdit()),
        }
        
        # 初始化類別選項
        categories = ["文學", "科學", "歷史", "藝術", "其他"]
        self.fields["category"][1].addItems(categories)
        
        row = 0
        
        # 1. 建立 ISBN 欄位 (包含自動填寫按鈕)
        main_layout.addWidget(QLabel("ISBN:"), row, 0)
        
        isbn_layout = QHBoxLayout() # 水平佈局
        self.isbn_edit = QLineEdit()
        self.fields["isbn"] = ("ISBN:", self.isbn_edit) # 補回 fields 字典方便後續讀取
        
        self.autofill_btn = QPushButton("✨ 自動填寫")
        self.autofill_btn.clicked.connect(self.on_autofill) # 連接事件
        # 如果是編輯模式，鎖定 ISBN 且禁用自動填寫
        if self.is_edit_mode:
            self.isbn_edit.setReadOnly(True)
            self.autofill_btn.setEnabled(False)
            
        isbn_layout.addWidget(self.isbn_edit)
        isbn_layout.addWidget(self.autofill_btn)
        
        main_layout.addLayout(isbn_layout, row, 1)
        row += 1

        # 2. 建立其他欄位 (迴圈生成)
        for key, (label_text, widget) in self.fields.items():
            if key == "isbn": continue # ISBN 已經手動處理過了
            
            main_layout.addWidget(QLabel(label_text), row, 0)
            main_layout.addWidget(widget, row, 1)
            row += 1

        # 3. 填入舊資料 (如果是編輯模式)
        if self.is_edit_mode and self.book_data:
            for key, (_, widget) in self.fields.items():
                if key in self.book_data:
                    value = self.book_data[key]
                    if value is None: value = ""
                    
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QComboBox):
                        index = widget.findText(value)
                        if index != -1:
                            widget.setCurrentIndex(index)

        # 4. 底部按鈕
        self.save_button = QPushButton("💾 儲存")
        self.save_button.clicked.connect(self.accept) 
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout, row, 0, 1, 2)

    # --- 新增功能：處理自動填寫邏輯 ---
    def on_autofill(self):
        isbn = self.isbn_edit.text().strip()
        if not isbn:
            QMessageBox.warning(self, "警告", "請先輸入 ISBN！")
            return
            
        try:
            # 呼叫我們剛剛在後端新增的 API
            api_url = f"{API_BASE_URL}/external/books/{isbn}"
            response = requests.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                
                # 自動填入欄位
                self.fields['title'][1].setText(data.get('title', ''))
                self.fields['author'][1].setText(data.get('author', ''))
                self.fields['url'][1].setText(data.get('url', ''))
                
                # 嘗試自動選擇類別
                cat_combo = self.fields['category'][1]
                category = data.get('category', '')
                index = cat_combo.findText(category)
                if index != -1:
                    cat_combo.setCurrentIndex(index)
                else:
                    cat_combo.setCurrentIndex(cat_combo.findText("其他"))
                    
                QMessageBox.information(self, "成功", "資料已自動載入！")
            elif response.status_code == 404:
                QMessageBox.warning(self, "查無資料", "Google Books 找不到此 ISBN。")
            else:
                QMessageBox.warning(self, "錯誤", f"API 回傳錯誤: {response.text}")
                
        except Exception as e:
             QMessageBox.critical(self, "連線失敗", f"無法連接後端: {str(e)}")

    def get_book_data(self):
        data = {}
        for key, (_, widget) in self.fields.items():
            if isinstance(widget, QLineEdit):
                data[key] = widget.text().strip()
            elif isinstance(widget, QComboBox):
                data[key] = widget.currentText()
                
        for key, value in data.items():
            if not value and key != 'isbn':
                 data[key] = None
        return data