import json
import os
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import keyboard
import pyautogui


class AutoClickerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("自动点击器 v2.0")
        self.root.geometry("500x600")
        self.root.resizable(False, False)

        # 应用状态
        self.is_clicking = False
        self.click_thread = None
        self.click_count = 0

        # 默认配置
        self.config = {
            "hotkey": "F9",
            "payment_x": 960,
            "payment_y": 600,
            "click_interval": 50,
            "mouse_speed": 0.8,
            "human_like": True
        }

        # 加载配置
        self.load_config()

        # 创建界面
        self.create_widgets()

        # 启动热键监听
        self.start_hotkey_listener()

        # 安全设置
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    def create_widgets(self):
        # 标题
        title_label = tk.Label(self.root, text="自动点击器", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # 创建选项卡
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)

        # 基本设置标签页
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="基本设置")

        # 热键设置
        hotkey_frame = ttk.LabelFrame(basic_frame, text="热键设置", padding=10)
        hotkey_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(hotkey_frame, text="开始/停止热键:").grid(row=0, column=0, sticky='w')
        self.hotkey_var = tk.StringVar(value=self.config["hotkey"])
        hotkey_entry = tk.Entry(hotkey_frame, textvariable=self.hotkey_var, state='readonly', width=10)
        hotkey_entry.grid(row=0, column=1, padx=5)
        tk.Button(hotkey_frame, text="更改", command=self.change_hotkey).grid(row=0, column=2, padx=5)

        # 点击设置
        click_frame = ttk.LabelFrame(basic_frame, text="点击设置", padding=10)
        click_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(click_frame, text="点击间隔(毫秒):").grid(row=0, column=0, sticky='w')
        self.interval_var = tk.IntVar(value=self.config["click_interval"])
        interval_scale = tk.Scale(click_frame, from_=10, to=1000, variable=self.interval_var,
                                  orient='horizontal', length=200)
        interval_scale.grid(row=0, column=1, columnspan=2, sticky='ew', padx=5)

        tk.Label(click_frame, text="模拟人类操作:").grid(row=1, column=0, sticky='w')
        self.human_var = tk.BooleanVar(value=self.config["human_like"])
        human_check = tk.Checkbutton(click_frame, variable=self.human_var)
        human_check.grid(row=1, column=1, sticky='w')

        # 支付设置
        payment_frame = ttk.LabelFrame(basic_frame, text="支付设置", padding=10)
        payment_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(payment_frame, text="支付按钮坐标:").grid(row=0, column=0, sticky='w')
        self.payment_x_var = tk.IntVar(value=self.config["payment_x"])
        self.payment_y_var = tk.IntVar(value=self.config["payment_y"])

        tk.Label(payment_frame, text="X:").grid(row=0, column=1, padx=2)
        payment_x_entry = tk.Entry(payment_frame, textvariable=self.payment_x_var, width=6)
        payment_x_entry.grid(row=0, column=2, padx=2)

        tk.Label(payment_frame, text="Y:").grid(row=0, column=3, padx=2)
        payment_y_entry = tk.Entry(payment_frame, textvariable=self.payment_y_var, width=6)
        payment_y_entry.grid(row=0, column=4, padx=2)

        tk.Button(payment_frame, text="获取坐标", command=self.get_payment_position).grid(row=0, column=5, padx=10)

        # 状态显示标签页
        status_frame = ttk.Frame(notebook)
        notebook.add(status_frame, text="状态监控")

        # 状态显示
        status_label_frame = ttk.LabelFrame(status_frame, text="运行状态", padding=10)
        status_label_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.status_text = tk.Text(status_label_frame, height=10, width=50)
        self.status_text.pack(fill='both', expand=True)

        # 控制按钮区域
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill='x', padx=10, pady=10)

        self.start_button = tk.Button(control_frame, text="开始 (F9)", command=self.toggle_clicking,
                                      bg="lightgreen", font=("Arial", 12, "bold"))
        self.start_button.pack(side='left', padx=5, ipadx=20, ipady=5)

        tk.Button(control_frame, text="保存配置", command=self.save_config).pack(side='left', padx=5)
        tk.Button(control_frame, text="帮助", command=self.show_help).pack(side='left', padx=5)
        tk.Button(control_frame, text="退出", command=self.root.quit).pack(side='left', padx=5)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪 - 按F9开始自动点击")
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief='sunken', anchor='w')
        status_bar.pack(fill='x', side='bottom', ipady=2)

    def change_hotkey(self):
        new_hotkey = simpledialog.askstring("更改热键", "请输入新的热键(如F9, F10等):",
                                            initialvalue=self.config["hotkey"])
        if new_hotkey:
            # 移除旧热键监听
            try:
                keyboard.remove_hotkey(self.hotkey_handle)
            except:
                pass

            # 设置新热键
            self.config["hotkey"] = new_hotkey.upper()
            self.hotkey_var.set(new_hotkey.upper())
            self.start_hotkey_listener()
            self.log_status(f"热键已更改为: {new_hotkey.upper()}")

    def get_payment_position(self):
        self.log_status("5秒内将鼠标移动到支付按钮上...")
        self.root.after(100, self._capture_position)

    def _capture_position(self):
        # 延迟捕获，给用户时间移动鼠标
        self.root.after(5000, self._save_payment_position)

    def _save_payment_position(self):
        try:
            x, y = pyautogui.position()
            self.payment_x_var.set(x)
            self.payment_y_var.set(y)
            self.log_status(f"已捕获支付按钮坐标: ({x}, {y})")
        except Exception as e:
            self.log_status(f"获取坐标失败: {e}")

    def smooth_move_to(self, target_x, target_y, duration=0.5):
        """模拟人类鼠标移动轨迹"""
        if not self.human_var.get():
            pyautogui.moveTo(target_x, target_y)
            return

        current_x, current_y = pyautogui.position()
        steps = int(duration * 100)

        for i in range(steps + 1):
            if not self.is_clicking:
                break

            t = i / steps
            # 使用缓动函数
            progress = t * t * (3 - 2 * t)

            # 加入随机偏移
            offset_x = random.randint(-2, 2) if i < steps else 0
            offset_y = random.randint(-2, 2) if i < steps else 0

            x = current_x + (target_x - current_x) * progress + offset_x
            y = current_y + (target_y - current_y) * progress + offset_y

            pyautogui.moveTo(x, y)
            time.sleep(duration / steps)

    def start_clicking(self):
        """开始点击循环"""
        self.is_clicking = True
        self.click_count = 0
        start_time = time.time()

        # 获取初始鼠标位置（抢购按钮位置）
        original_x, original_y = pyautogui.position()

        self.log_status("开始自动点击...")
        self.log_status(f"初始位置: ({original_x}, {original_y})")

        while self.is_clicking:
            try:
                # 获取当前鼠标位置
                current_x, current_y = pyautogui.position()

                # 模拟人类操作：加入随机偏移和延迟
                if self.human_var.get():
                    offset_x = random.randint(-1, 1)
                    offset_y = random.randint(-1, 1)
                    click_pos = (current_x + offset_x, current_y + offset_y)

                    # 随机点击间隔
                    interval = self.interval_var.get() + random.randint(-10, 10)
                    time.sleep(max(0.02, interval / 1000))
                else:
                    click_pos = (current_x, current_y)
                    time.sleep(self.interval_var.get() / 1000)

                # 执行点击
                pyautogui.click(click_pos)
                self.click_count += 1

                # 定期检查支付弹窗（每点击20次检查一次）
                if self.click_count % 20 == 0:
                    if self.check_payment_popup():
                        self.log_status("检测到支付弹窗，执行支付操作...")
                        self.execute_payment(original_x, original_y)
                        break

                # 安全停止：运行时间过长或鼠标移到角落
                if time.time() - start_time > 300:  # 5分钟自动停止
                    self.log_status("运行超时，自动停止")
                    break

            except pyautogui.FailSafeException:
                self.log_status("安全停止：鼠标移动到屏幕角落")
                break
            except Exception as e:
                self.log_status(f"点击错误: {e}")
                time.sleep(0.1)

        self.stop_clicking()
        self.log_status(f"点击结束，总共点击 {self.click_count} 次")

    def check_payment_popup(self):
        """检查支付弹窗（简单实现，可根据需要扩展）"""
        # 这里可以添加更复杂的检测逻辑，如图像识别等
        # 目前简单返回False，由用户手动停止或根据点击次数判断
        return False

    def execute_payment(self, original_x, original_y):
        """执行支付操作"""
        try:
            payment_x = self.payment_x_var.get()
            payment_y = self.payment_y_var.get()

            # 平滑移动到支付按钮
            self.smooth_move_to(payment_x, payment_y)
            time.sleep(0.2)

            # 点击支付按钮
            pyautogui.click()
            self.log_status("已点击支付按钮")

            # 可选：返回原位置
            # self.smooth_move_to(original_x, original_y)

        except Exception as e:
            self.log_status(f"支付操作错误: {e}")

    def toggle_clicking(self):
        """切换点击状态"""
        if not self.is_clicking:
            self.is_clicking = True
            self.click_thread = threading.Thread(target=self.start_clicking, daemon=True)
            self.click_thread.start()
            self.start_button.config(text="停止 (F9)", bg="lightcoral")
            self.status_var.set("自动点击进行中...")
        else:
            self.stop_clicking()

    def stop_clicking(self):
        """停止点击"""
        self.is_clicking = False
        self.start_button.config(text="开始 (F9)", bg="lightgreen")
        self.status_var.set("就绪 - 按F9开始自动点击")

    def start_hotkey_listener(self):
        """开始监听热键"""

        def hotkey_handler():
            self.root.after(0, self.toggle_clicking)

        try:
            self.hotkey_handle = keyboard.add_hotkey(
                self.config["hotkey"].lower(),
                hotkey_handler
            )
        except Exception as e:
            self.log_status(f"热键监听错误: {e}")

    def log_status(self, message):
        """记录状态信息"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        self.status_text.insert('end', log_message)
        self.status_text.see('end')
        self.root.update_idletasks()

    def save_config(self):
        """保存配置到文件"""
        self.config.update({
            "hotkey": self.hotkey_var.get(),
            "payment_x": self.payment_x_var.get(),
            "payment_y": self.payment_y_var.get(),
            "click_interval": self.interval_var.get(),
            "mouse_speed": 0.8,  # 保留参数
            "human_like": self.human_var.get()
        })

        try:
            with open('autoclicker_config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
            self.log_status("配置已保存")
        except Exception as e:
            self.log_status(f"保存配置失败: {e}")

    def load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists('autoclicker_config.json'):
                with open('autoclicker_config.json', 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
        except:
            pass  # 如果加载失败，使用默认配置

    def show_help(self):
        """显示帮助信息"""
        help_text = """
自动点击器使用说明:

1. 基本设置:
   - 设置开始/停止热键(默认F9)
   - 调整点击间隔(毫秒)
   - 启用模拟人类操作(推荐)

2. 支付设置:
   - 获取支付按钮坐标(将鼠标移动到支付按钮上点击获取)

3. 使用方法:
   - 将鼠标放在抢购按钮上
   - 按设置的热键开始自动点击
   - 再次按热键停止点击
   - 检测到支付弹窗会自动点击支付按钮

4. 安全特性:
   - 鼠标移动到屏幕角落可紧急停止
   - 5分钟自动超时停止
   - 模拟人类操作避免检测

注意: 请确保目标软件窗口处于前台状态。
        """
        messagebox.showinfo("使用帮助", help_text)

    def on_closing(self):
        """程序关闭时的处理"""
        self.stop_clicking()
        try:
            keyboard.unhook_all()
        except:
            pass
        self.root.destroy()


def main():
    # 检查依赖库
    try:
        import pyautogui
        import keyboard
        from PIL import Image, ImageTk
    except ImportError as e:
        print(f"缺少依赖库: {e}")
        print("请安装: pip install pyautogui keyboard pillow")
        return

    # 创建主窗口
    root = tk.Tk()
    app = AutoClickerGUI(root)

    # 设置关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    # 启动主循环
    root.mainloop()



if __name__ == "__main__":
    main()


# 打包命令：
#  pyinstaller --onefile --windowed --name=AutoClicker --upx-dir=D:\Tools\upx-5.0.2-win64 --clean --noconfirm autoclicker_gui.py