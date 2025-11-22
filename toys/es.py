import tkinter as tk
from tkinter import ttk, messagebox
import json
import pyperclip
import sys  # 导入 sys 用于打印完整的错误信息
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, AuthenticationException, NotFoundError
from pprint import pprint  # 用于美观地打印 Python 字典/JSON


# 确保安装了所需的库：
# pip install elasticsearch pyperclip

class ESQueryTool:
    def __init__(self, root):
        self.root = root
        self.root.title("ES 简易查询工具 (v2.1 - 调试日志增强版)")
        self.root.geometry("1000x650")
        self.es = None
        self.indices = []
        self.current_index_fields = []
        self.current_hits = {}

        # ... (GUI 初始化部分与上一个版本相同，这里省略以保持代码简洁，但功能是完整的) ...
        # --- 1. 连接与认证区域 ---
        conn_frame = ttk.LabelFrame(root, text="服务器连接与认证 (支持 Basic Auth)", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)

        conn_widgets = ttk.Frame(conn_frame)
        conn_widgets.pack(fill="x")

        ttk.Label(conn_widgets, text="Host:").pack(side="left", padx=(0, 5))
        self.host_entry = ttk.Entry(conn_widgets, width=25)
        self.host_entry.insert(0, "http://localhost:9200")
        self.host_entry.pack(side="left", padx=(0, 15))

        ttk.Label(conn_widgets, text="用户:").pack(side="left", padx=(0, 5))
        self.user_entry = ttk.Entry(conn_widgets, width=15)
        self.user_entry.pack(side="left", padx=(0, 15))

        ttk.Label(conn_widgets, text="密码:").pack(side="left", padx=(0, 5))
        self.pass_entry = ttk.Entry(conn_widgets, width=15, show="*")
        self.pass_entry.pack(side="left", padx=(0, 15))

        ttk.Button(conn_widgets, text="连接并获取索引", command=self.connect_es).pack(side="left", padx=(10, 20))

        self.status_lbl = ttk.Label(conn_widgets, text="状态: 未连接", foreground="red")
        self.status_lbl.pack(side="left", padx=10)

        # --- 2. 查询构建区域 ---
        query_frame = ttk.LabelFrame(root, text="查询条件构建器", padding=10)
        query_frame.pack(fill="x", padx=10, pady=5)

        row1 = ttk.Frame(query_frame)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="选择索引 (Index):").pack(side="left")
        self.index_combo = ttk.Combobox(row1, state="readonly", width=30)
        self.index_combo.bind("<<ComboboxSelected>>", self.fetch_fields_for_index)
        self.index_combo.pack(side="left", padx=5)

        row2 = ttk.Frame(query_frame)
        row2.pack(fill="x", pady=5)
        ttk.Label(row2, text="查询方式:").pack(side="left")
        self.query_type = tk.StringVar(value="match_all")

        types = [
            ("查看所有 (Match All)", "match_all"),
            ("关键词搜索 (Match - 模糊)", "match"),
            ("精确匹配 (Term - 等于)", "term"),
            ("范围查询 (Range - 时间/数字)", "range")
        ]

        for text, mode in types:
            ttk.Radiobutton(row2, text=text, variable=self.query_type, value=mode, command=self.update_inputs).pack(
                side="left", padx=10)

        self.input_frame = ttk.Frame(query_frame)
        self.input_frame.pack(fill="x", pady=10)

        self.field_combo = None
        self.value_entry = None
        self.start_entry = None
        self.end_entry = None

        self.update_inputs()

        ttk.Button(query_frame, text="执行查询", command=self.execute_search).pack(anchor="e")

        # --- 3. 结果展示区域 ---
        result_frame = ttk.LabelFrame(root, text="查询结果 (双击行查看详情)", padding=10)
        result_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("_id", "_score", "source_snippet")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        self.tree.heading("_id", text="ID")
        self.tree.heading("_score", text="匹配分")
        self.tree.heading("source_snippet", text="数据摘要 (Source)")

        self.tree.column("_id", width=150, anchor="w")
        self.tree.column("_score", width=80, anchor="center")
        self.tree.column("source_snippet", width=600, anchor="w")

        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<Double-1>", self.on_tree_double_click)

    # --- 核心逻辑 ---

    def connect_es(self):
        host = self.host_entry.get()
        username = self.user_entry.get()
        password = self.pass_entry.get()

        print("--- 调试日志: 连接尝试 ---")
        print(f"尝试连接 Host: {host}")

        auth_params = {}
        if username and password:
            auth_params = {'basic_auth': (username, password)}
            print(f"使用 Basic Auth，用户: {username}，密码长度: {len(password)}")

        try:
            self.es = Elasticsearch(hosts=host, **auth_params)

            # 尝试 Ping，这是最主要的连接测试
            ping_result = self.es.ping()
            print(f"ES Ping 结果: {ping_result}")

            if not ping_result:
                raise ConnectionError("Ping 失败。这通常意味着服务未运行、地址错误或防火墙阻止。")

            # 获取所有索引
            print("尝试获取索引列表...")
            indices = list(self.es.indices.get_alias(index="*").keys())
            indices.sort()
            self.indices = indices
            self.index_combo['values'] = self.indices

            if self.indices:
                self.index_combo.current(0)
                self.fetch_fields_for_index()

            self.status_lbl.config(text="状态: 已连接", foreground="green")
            messagebox.showinfo("成功", f"连接成功！发现 {len(indices)} 个索引。")
            print("连接成功！")

        except AuthenticationException:
            print("\n!!! 错误类型: 认证失败 (AuthenticationException) !!!")
            print("请检查用户名和密码是否正确。")
            self.status_lbl.config(text="状态: 认证失败", foreground="red")
            messagebox.showerror("连接错误", "认证失败：用户名或密码错误。")

        except ConnectionError as e:
            print("\n!!! 错误类型: 连接错误 (ConnectionError) !!!")
            print(f"详细错误信息: {e}")
            self.status_lbl.config(text="状态: 连接失败", foreground="red")
            messagebox.showerror("连接错误", f"连接失败，详细错误信息请查看控制台。")

        except Exception as e:
            print("\n!!! 错误类型: 未知错误 (General Exception) !!!")
            print(f"详细错误信息: {e}")
            self.status_lbl.config(text="状态: 连接失败", foreground="red")
            messagebox.showerror("连接错误", f"发生未知错误: {str(e)}。详细信息已打印到控制台。")

            # 打印完整的堆栈跟踪 (Traceback)
            import traceback
            traceback.print_exc(file=sys.stdout)
        finally:
            print("--- 调试日志: 连接尝试结束 ---\n")

    def fetch_fields_for_index(self, event=None):
        """获取当前选中索引的字段列表"""
        index = self.index_combo.get()
        print(f"--- 调试日志: 获取字段 ---")
        print(f"尝试获取索引 '{index}' 的 Mapping")

        if not index or not self.es:
            return

        self.current_index_fields = []
        try:
            mapping = self.es.indices.get_mapping(index=index)

            if not mapping or index not in mapping:
                print("Mapping 结果为空或结构异常。")
                return

            # 解析 mapping 逻辑 (同上一个版本)
            properties = list(mapping[index]['mappings']['properties'].items())
            fields = []
            for field_name, field_props in properties:
                if 'properties' in field_props:
                    fields.append(f"{field_name} (Object)")
                else:
                    fields.append(field_name)

            fields.sort()
            self.current_index_fields = fields
            print(f"成功获取 {len(fields)} 个字段。")
            # 更新输入区域（确保字段下拉框更新）
            self.update_inputs()

        except NotFoundError:
            print("错误: 索引未找到。")
            messagebox.showwarning("警告", f"索引 '{index}' 未找到。")
        except Exception as e:
            print(f"错误: 获取字段列表时出错: {e}")
            import traceback
            traceback.print_exc(file=sys.stdout)
            messagebox.showerror("字段获取错误", f"获取字段列表时出错，请查看控制台日志。")
        finally:
            print("--- 调试日志: 获取字段结束 ---\n")

    def execute_search(self):
        """执行查询并将结果渲染到表格"""
        if not self.es:
            messagebox.showwarning("警告", "请先连接 ES 服务器")
            return

        index = self.index_combo.get()
        mode = self.query_type.get()
        body = {}

        try:
            # ... (DSL 构建逻辑同上一个版本) ...
            if mode == "match_all":
                body = {"query": {"match_all": {}}}

            elif mode in ["match", "term", "range"]:
                field = self.field_combo.get() if self.field_combo else None
                if not field or "(Object)" in field:
                    messagebox.showwarning("警告", "请选择有效的字段名或先获取字段列表。")
                    return

                if mode == "match":
                    val = self.value_entry.get()
                    if not val: return
                    body = {"query": {"match": {field: val}}}

                elif mode == "term":
                    val = self.value_entry.get()
                    if not val: return
                    body = {"query": {"term": {field: val}}}

                elif mode == "range":
                    gte = self.start_entry.get()
                    lte = self.end_entry.get()

                    range_cond = {}
                    if gte: range_cond["gte"] = gte
                    if lte: range_cond["lte"] = lte

                    if not range_cond:
                        messagebox.showwarning("警告", "范围查询至少需要一个值。")
                        return

                    body = {"query": {"range": {field: range_cond}}}

            print("--- 调试日志: 执行查询 ---")
            print(f"查询索引: {index}")
            print("查询 DSL (Query Body):")
            pprint(body)  # 使用 pprint 美观打印查询体

            # 执行查询
            res = self.es.search(index=index, body=body, size=50)
            self.render_results(res)
            print(f"查询成功，耗时 {res['took']}ms，总命中数: {res['hits']['total']['value']}")
            print("--- 调试日志: 执行查询结束 ---\n")

        except Exception as e:
            print("\n!!! 错误类型: 查询执行错误 !!!")
            import traceback
            traceback.print_exc(file=sys.stdout)  # 打印完整的堆栈跟踪
            messagebox.showerror("查询出错", f"查询执行失败，详细错误信息已打印到控制台。")

    # --- 其他辅助方法 (update_inputs, render_results, show_json_window, copy_to_clipboard) 与上一个版本保持一致 ---
    def update_inputs(self):
        # ... (与上一个版本相同) ...
        for widget in self.input_frame.winfo_children():
            widget.destroy()

        mode = self.query_type.get()

        if mode == "match_all":
            ttk.Label(self.input_frame, text="无需输入条件，将返回前 50 条数据。").pack(side="left")

        elif mode in ["match", "term", "range"]:
            ttk.Label(self.input_frame, text="字段名 (Field):").pack(side="left")
            self.field_combo = ttk.Combobox(self.input_frame, state="readonly", width=25)
            self.field_combo['values'] = self.current_index_fields
            if self.current_index_fields:
                self.field_combo.current(0)
            self.field_combo.pack(side="left", padx=5)

            if not self.current_index_fields:
                ttk.Label(self.input_frame, text="提示: 请先连接 ES 并选择一个有数据的索引以获取字段。",
                          foreground="gray").pack(side="left", padx=10)

            if mode in ["match", "term"]:
                ttk.Label(self.input_frame, text="值 (Value):").pack(side="left")
                self.value_entry = ttk.Entry(self.input_frame, width=30)
                self.value_entry.pack(side="left", padx=5)

            elif mode == "range":
                ttk.Label(self.input_frame, text="大于等于 (gte):").pack(side="left")
                self.start_entry = ttk.Entry(self.input_frame, width=20)
                self.start_entry.pack(side="left", padx=5)

                ttk.Label(self.input_frame, text="小于等于 (lte):").pack(side="left")
                self.end_entry = ttk.Entry(self.input_frame, width=20)
                self.end_entry.pack(side="left", padx=5)

    def render_results(self, res):
        # ... (与上一个版本相同) ...
        for i in self.tree.get_children():
            self.tree.delete(i)

        self.current_hits = {}
        hits = res['hits']['hits']

        if not hits:
            messagebox.showinfo("结果", "未找到匹配的数据")
            return

        for hit in hits:
            _id = hit['_id']
            _score = hit['_score']
            _source = hit.get('_source', {})

            self.current_hits[_id] = _source

            source_str = str(_source)
            if len(source_str) > 100:
                source_str = source_str[:97] + "..."

            self.tree.insert("", "end", iid=_id, values=(_id, _score, source_str))

    def on_tree_double_click(self, event):
        # ... (与上一个版本相同) ...
        try:
            item_id = self.tree.selection()[0]
            data = self.current_hits.get(item_id)

            if data:
                self.show_json_window(item_id, data)
        except IndexError:
            pass

    def show_json_window(self, doc_id, data):
        # ... (与上一个版本相同) ...
        top = tk.Toplevel(self.root)
        top.title(f"文档详情: {doc_id}")
        top.geometry("700x600")

        pretty_json = json.dumps(data, indent=4, ensure_ascii=False)

        copy_btn = ttk.Button(top, text="复制完整 JSON",
                              command=lambda: self.copy_to_clipboard(pretty_json))
        copy_btn.pack(pady=5, padx=10, anchor="w")

        text_area = tk.Text(top, wrap="word", font=("Courier New", 10))
        text_area.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        text_area.insert("1.0", pretty_json)

    def copy_to_clipboard(self, text):
        # ... (与上一个版本相同) ...
        try:
            pyperclip.copy(text)
            messagebox.showinfo("成功", "完整 JSON 已复制到剪贴板！", parent=self.root)
        except pyperclip.PyperclipException:
            messagebox.showerror("错误", "无法访问剪贴板，请检查是否安装了必要的依赖或运行环境。")


if __name__ == "__main__":
    root = tk.Tk()
    app = ESQueryTool(root)
    root.mainloop()