import sys
import json
import sqlite3
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextBrowser,
                             QComboBox, QMessageBox, QCheckBox, QFrame,
                             QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


# ===========================
# 1. 数据模型层 (Model)
# ===========================

@dataclass
class Question:
    id: int
    type: str
    stem: str
    answer: str
    tags: str = "未分类"
    is_marked: bool = False


class DataSource(ABC):
    @abstractmethod
    def load_questions(self) -> List[Question]:
        pass

    @abstractmethod
    def update_mark(self, q_id: int, is_marked: bool):
        pass

    @abstractmethod
    def add_question(self, stem: str, answer: str, tags: str, q_type: str = "qa") -> bool:
        """新增题目"""
        pass


class JsonDataSource(DataSource):
    def __init__(self, filepath="questions_v2.json"):
        self.filepath = filepath
        if not os.path.exists(self.filepath):
            self._create_dummy_data()

    def _create_dummy_data(self):
        data = [
            {"id": 1, "type": "qa", "stem": "示例题目：点击上方➕号添加你自己的题目。", "answer": "这是答案区域。",
             "tags": "新手引导", "is_marked": False}
        ]
        self._save_data(data)

    def _save_data(self, data):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_questions(self) -> List[Question]:
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            return [Question(d['id'], d['type'], d['stem'], d['answer'], d.get('tags', ''), d.get('is_marked', False))
                    for d in raw]
        except:
            return []

    def update_mark(self, q_id: int, is_marked: bool):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                if item['id'] == q_id:
                    item['is_marked'] = is_marked
                    break
            self._save_data(data)
        except Exception as e:
            print(f"JSON Update Error: {e}")

    def add_question(self, stem: str, answer: str, tags: str, q_type: str = "qa") -> bool:
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 计算新ID：取最大ID + 1
            new_id = 1
            if data:
                new_id = max(item['id'] for item in data) + 1

            new_item = {
                "id": new_id,
                "type": q_type,
                "stem": stem,
                "answer": answer,
                "tags": tags,
                "is_marked": False
            }
            data.append(new_item)
            self._save_data(data)
            return True
        except Exception as e:
            print(f"JSON Add Error: {e}")
            return False


class SqliteDataSource(DataSource):
    def __init__(self, db_path="questions_v2.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS questions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, stem TEXT, answer TEXT, tags TEXT, is_marked INTEGER)''')
        conn.commit()
        conn.close()

    def load_questions(self) -> List[Question]:
        qs = []
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, type, stem, answer, tags, is_marked FROM questions")
        for row in c.fetchall():
            qs.append(Question(row[0], row[1], row[2], row[3], row[4], bool(row[5])))
        conn.close()
        return qs

    def update_mark(self, q_id: int, is_marked: bool):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE questions SET is_marked = ? WHERE id = ?", (1 if is_marked else 0, q_id))
        conn.commit()
        conn.close()

    def add_question(self, stem: str, answer: str, tags: str, q_type: str = "qa") -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("INSERT INTO questions (type, stem, answer, tags, is_marked) VALUES (?, ?, ?, ?, ?)",
                      (q_type, stem, answer, tags, 0))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"DB Add Error: {e}")
            return False


# ===========================
# 2. 界面组件层 (View)
# ===========================

class AddQuestionDialog(QDialog):
    """新增题目的模态弹窗"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加新题目")
        self.resize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # 输入控件
        self.stem_edit = QTextEdit()
        self.stem_edit.setPlaceholderText("在这里输入问题 (支持 Markdown)...")
        self.answer_edit = QTextEdit()
        self.answer_edit.setPlaceholderText("在这里输入答案/解析...")
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("例如: Python, 网络 (用逗号分隔)")

        form_layout.addRow("题干:", self.stem_edit)
        form_layout.addRow("答案:", self.answer_edit)
        form_layout.addRow("标签:", self.tags_edit)

        layout.addLayout(form_layout)

        # 按钮
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_data(self):
        return {
            "stem": self.stem_edit.toPlainText().strip(),
            "answer": self.answer_edit.toPlainText().strip(),
            "tags": self.tags_edit.text().strip()
        }


class QAWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("📝 题干:"))
        self.stem_browser = QTextBrowser()
        self.stem_browser.setStyleSheet("font-size: 16px; background: #f9f9f9; border: 1px solid #ccc;")
        layout.addWidget(self.stem_browser, 2)

        layout.addWidget(QLabel("💡 参考答案:"))
        self.ans_browser = QTextBrowser()
        self.ans_browser.setStyleSheet("font-size: 15px; background: #fff; border: 1px solid #ddd;")
        layout.addWidget(self.ans_browser, 3)

        self.mask_html = "<div style='color:#999; text-align:center; margin-top:40px;'><i>(答案已隐藏，思考后查看)</i></div>"

    def render(self, q: Question, show_answer: bool):
        # 题干
        self.stem_browser.setMarkdown(q.stem) if "###" in q.stem or "**" in q.stem else self.stem_browser.setHtml(
            q.stem)
        # 答案
        if show_answer:
            if "<br>" in q.answer or "<div>" in q.answer:
                self.ans_browser.setHtml(q.answer)
            else:
                self.ans_browser.setMarkdown(q.answer)
        else:
            self.ans_browser.setHtml(self.mask_html)


# ===========================
# 3. 主控制器 (Controller)
# ===========================

class InterviewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("刷题神器")
        self.resize(900, 750)

        self.current_source: DataSource = None
        self.all_questions: List[Question] = []
        self.display_questions: List[Question] = []
        self.current_index = 0
        self.is_answer_shown = False

        self.init_ui()
        self.load_source("json")

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # --- 顶部功能区 ---
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background-color: #e3f2fd; border-radius: 5px;")
        top_layout = QHBoxLayout(filter_frame)

        top_layout.addWidget(QLabel("数据源:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["JSON", "Database"])
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        top_layout.addWidget(self.source_combo)

        # 添加题目按钮 (NEW)
        self.btn_add = QPushButton("➕ 添加题目")
        self.btn_add.setStyleSheet("background-color: #4caf50; color: white; font-weight: bold;")
        self.btn_add.clicked.connect(self.open_add_dialog)
        top_layout.addWidget(self.btn_add)

        top_layout.addSpacing(10)

        top_layout.addWidget(QLabel("🏷 标签:"))
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.setMinimumWidth(120)
        self.tag_filter_combo.addItem("全部")
        self.tag_filter_combo.currentTextChanged.connect(self.apply_filters)
        top_layout.addWidget(self.tag_filter_combo)

        self.shuffle_cb = QCheckBox("🎲 乱序")
        self.shuffle_cb.stateChanged.connect(self.apply_filters)
        top_layout.addWidget(self.shuffle_cb)

        top_layout.addStretch()
        self.lbl_count = QLabel("0/0")
        top_layout.addWidget(self.lbl_count)

        layout.addWidget(filter_frame)

        # --- 题目区 ---
        self.qa_widget = QAWidget()
        layout.addWidget(self.qa_widget)

        # --- 底部控制区 ---
        btn_layout = QHBoxLayout()
        self.btn_prev = QPushButton("⬅ 上一题")
        self.btn_prev.clicked.connect(self.go_prev)

        self.btn_show = QPushButton("显示答案 (Space)")
        self.btn_show.setShortcut(Qt.Key.Key_Space)
        self.btn_show.setStyleSheet("""
            QPushButton { background-color: #007bff; color: white; font-weight: bold; padding: 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #0056b3; }
        """)
        self.btn_show.clicked.connect(self.toggle_answer)

        self.btn_next = QPushButton("下一题 ➡")
        self.btn_next.clicked.connect(self.go_next)

        self.btn_mark = QPushButton("🤯 记不住")
        self.btn_mark.setCheckable(True)
        self.btn_mark.clicked.connect(self.toggle_mark_status)
        self.btn_mark.setStyleSheet("""
            QPushButton { border: 1px solid #d9534f; color: #d9534f; padding: 10px; border-radius: 4px; }
            QPushButton:checked { background-color: #d9534f; color: white; }
        """)

        btn_layout.addWidget(self.btn_prev)
        btn_layout.addWidget(self.btn_show)
        btn_layout.addWidget(self.btn_mark)
        btn_layout.addWidget(self.btn_next)

        layout.addLayout(btn_layout)

    # --- 逻辑处理 ---

    def load_source(self, type_str):
        self.current_source = JsonDataSource() if type_str == "json" else SqliteDataSource()
        self.reload_data()

    def reload_data(self):
        """重新从源加载数据并刷新界面"""
        self.all_questions = self.current_source.load_questions()
        self.refresh_tags()
        self.apply_filters()

    def open_add_dialog(self):
        """打开新增题目弹窗"""
        dialog = AddQuestionDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['stem'] or not data['answer']:
                QMessageBox.warning(self, "错误", "题干和答案不能为空！")
                return

            # 调用 Model 保存
            success = self.current_source.add_question(data['stem'], data['answer'], data['tags'])

            if success:
                QMessageBox.information(self, "成功", "题目已添加！")
                self.reload_data()  # 关键：刷新数据

                # 自动跳转到最后一题（通常是刚添加的题）
                # 这里为了体验，我们不强制跳转，但刷新后如果处于“全部”标签，新题会出现在列表里
            else:
                QMessageBox.critical(self, "错误", "保存失败，请检查文件或数据库权限。")

    def refresh_tags(self):
        current = self.tag_filter_combo.currentText()
        self.tag_filter_combo.blockSignals(True)
        self.tag_filter_combo.clear()
        self.tag_filter_combo.addItems(["全部", "⭐ 只看错题"])

        tags = set()
        for q in self.all_questions:
            for t in q.tags.replace('，', ',').split(','):
                if t.strip(): tags.add(t.strip())

        self.tag_filter_combo.addItems(sorted(list(tags)))

        idx = self.tag_filter_combo.findText(current)
        if idx >= 0:
            self.tag_filter_combo.setCurrentIndex(idx)
        else:
            self.tag_filter_combo.setCurrentIndex(0)
        self.tag_filter_combo.blockSignals(False)

    def apply_filters(self):
        filter_txt = self.tag_filter_combo.currentText()
        is_shuffle = self.shuffle_cb.isChecked()

        if filter_txt == "全部":
            filtered = list(self.all_questions)
        elif filter_txt == "⭐ 只看错题":
            filtered = [q for q in self.all_questions if q.is_marked]
        else:
            filtered = [q for q in self.all_questions if filter_txt in q.tags]

        if is_shuffle:
            random.shuffle(filtered)
        else:
            filtered.sort(key=lambda x: x.id)

        self.display_questions = filtered
        self.current_index = 0
        self.refresh_view()

    def refresh_view(self):
        total = len(self.display_questions)
        if total == 0:
            self.lbl_count.setText("0/0")
            self.qa_widget.stem_browser.setText("")
            self.qa_widget.ans_browser.setText("")
            self.btn_show.setEnabled(False)
            self.btn_mark.setEnabled(False)
            return

        if self.current_index >= total: self.current_index = total - 1
        q = self.display_questions[self.current_index]

        self.lbl_count.setText(f"{self.current_index + 1}/{total}")
        self.is_answer_shown = False
        self.qa_widget.render(q, False)

        self.btn_show.setText("👁 显示答案 (Space)")
        self.btn_show.setEnabled(True)
        self.btn_mark.setEnabled(True)
        self.btn_mark.setChecked(q.is_marked)
        self.btn_mark.setText("✅ 已加入错题本" if q.is_marked else "🤯 记不住")

    def on_source_changed(self, idx):
        self.load_source("json" if idx == 0 else "db")

    def toggle_answer(self):
        if not self.display_questions: return
        self.is_answer_shown = True
        self.qa_widget.render(self.display_questions[self.current_index], True)
        self.btn_show.setText("已显示")
        self.btn_show.setEnabled(False)

    def go_next(self):
        if self.current_index < len(self.display_questions) - 1:
            self.current_index += 1
            self.refresh_view()
        else:
            QMessageBox.information(self, "提示", "本组题目已刷完！")

    def go_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.refresh_view()

    def toggle_mark_status(self):
        if not self.display_questions: return
        q = self.display_questions[self.current_index]
        new_status = not q.is_marked
        q.is_marked = new_status
        self.btn_mark.setChecked(new_status)
        self.btn_mark.setText("✅ 已加入错题本" if new_status else "🤯 记不住")
        self.current_source.update_mark(q.id, new_status)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))
    win = InterviewApp()
    win.show()
    sys.exit(app.exec())