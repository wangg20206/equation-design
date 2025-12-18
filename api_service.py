# api_service.py
import requests
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

# --- Pydantic 資料模型 ---
class Book(BaseModel):
    title: str       # 書名
    author: str      # 作者
    isbn: str        # 國際標準書號 (唯一識別碼)
    category: str    # 類別 (e.g., 文學, 科學)
    url: Optional[str] = None # 網址 (選填)

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None

# --- 資料庫模擬與 FastAPI 應用初始化 ---
app = FastAPI(title="Virtual Library Manager API")

# 使用字典模擬資料庫儲存： {isbn: Book_object}
db: Dict[str, Book] = {
    "978-0321765723": Book(
        title="The Lord of the Rings", 
        author="J.R.R. Tolkien", 
        isbn="978-0321765723", 
        category="文學", 
        url="example.com/lotr"
    ),
    "978-0321990497": Book(
        title="Clean Code", 
        author="Robert C. Martin", 
        isbn="978-0321990497", 
        category="科學", 
        url="example.com/cleancode"
    ),
    "978-1503251700": Book(
        title="Pride and Prejudice", 
        author="Jane Austen", 
        isbn="978-1503251700", 
        category="文學", 
    ),
}

# --- CRUD API 接口 ---

@app.get("/books", response_model=List[Book], tags=["CRUD"])
def get_all_books():
    """回傳所有書籍列表"""
    return list(db.values())

@app.get("/books/{isbn}", response_model=Book, tags=["CRUD"])
def get_book(isbn: str):
    """根據 ISBN 查詢單本書籍資料"""
    if isbn not in db:
        raise HTTPException(status_code=404, detail="Book not found")
    return db[isbn]

@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED, tags=["CRUD"])
def create_book(book: Book):
    """新增一本新書"""
    if book.isbn in db:
        raise HTTPException(status_code=400, detail="Book with this ISBN already exists")
    db[book.isbn] = book
    return book

@app.put("/books/{isbn}", response_model=Book, tags=["CRUD"])
def update_book(isbn: str, updated_book: BookUpdate):
    """更新指定 ISBN 的書籍資料"""
    if isbn not in db:
        raise HTTPException(status_code=404, detail="Book not found")
    
    update_data = updated_book.model_dump(exclude_unset=True)
    existing_book = db[isbn].model_dump()
    existing_book.update(update_data)
    
    db[isbn] = Book(**existing_book)
    return db[isbn]

@app.delete("/books/{isbn}", status_code=status.HTTP_204_NO_CONTENT, tags=["CRUD"])
def delete_book(isbn: str):
    """根據 ISBN 刪除書籍"""
    if isbn in db:
        del db[isbn]
    return

# --- 統計 API 接口 ---

@app.get("/stats", tags=["Stats"])
def get_book_stats():
    """回傳書籍類別的統計數量 (e.g., {"文學": 10, "科學": 5})"""
    category_counts = {}
    for book in db.values():
        category = book.category
        category_counts[category] = category_counts.get(category, 0) + 1
    return category_counts


# --- 外部 ISBN 查詢 API ---
@app.get("/external/books/{isbn}", tags=["External"])
def fetch_external_book_info(isbn: str):
    """
    呼叫 Google Books API 取得書籍資訊，
    並整理成符合我們 Book 模型格式的 JSON 回傳。
    """
    google_api_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    
    try:
        response = requests.get(google_api_url)
        data = response.json()
        
        if "items" not in data:
            raise HTTPException(status_code=404, detail="Google Books API 找不到該書籍")
            
        volume_info = data["items"][0]["volumeInfo"]
        
        # 提取並整理資料
        return {
            "title": volume_info.get("title", "未知書名"),
            "author": ", ".join(volume_info.get("authors", ["未知作者"])),
            "isbn": isbn,
            # 嘗試抓取第一個分類，若無則標示未分類
            "category": volume_info.get("categories", ["其他"])[0], 
            # 優先抓取資訊頁面網址
            "url": volume_info.get("infoLink", "") 
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"外部 API 連線錯誤: {str(e)}")
    