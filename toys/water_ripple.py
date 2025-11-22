import pygame
import numpy as np
import time

# --- 配置参数 ---
WIDTH, HEIGHT = 800, 600
DAMPING = 0.97  # 阻尼系数 (0.0 ~ 1.0)，越小波纹消失越快，越大波纹传得越远
FPS = 60

# --- 初始化 Pygame ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Python 水波纹模拟 (按住鼠标控制水滴大小)")
clock = pygame.time.Clock()

# --- 初始化物理缓冲区 ---
# 使用两个缓冲区来存储波的高度场
# buffer1: 当前帧的高度
# buffer2: 上一帧的高度 (同时也用于计算下一帧)
buffer1 = np.zeros((WIDTH, HEIGHT), dtype=np.float32)
buffer2 = np.zeros((WIDTH, HEIGHT), dtype=np.float32)

# --- 生成背景图片 ---
# 为了看清波纹折射，我们需要一个有纹理的背景
# 这里程序化生成一个蓝色的“海底”石头纹理
background_surf = pygame.Surface((WIDTH, HEIGHT))
background_array = np.zeros((WIDTH, HEIGHT, 3), dtype=np.int32)

# 创建简单的渐变和噪点背景
for y in range(HEIGHT):
    # 垂直蓝色渐变
    blue_val = int(100 + (y / HEIGHT) * 155)
    background_array[:, y, 2] = blue_val  # Blue channel
    background_array[:, y, 1] = int(blue_val * 0.6)  # Green channel
    background_array[:, y, 0] = 0  # Red channel

# 添加一些随机噪点/石头来增强折射效果
noise = np.random.randint(0, 50, (WIDTH, HEIGHT, 3))
background_array = np.clip(background_array + noise, 0, 255)

# 将numpy数组转换为pygame surface以备用
pygame.surfarray.blit_array(background_surf, background_array)
# 获取背景的像素数组用于实时折射计算
bg_arr_source = pygame.surfarray.array3d(background_surf)


def add_drop(x, y, radius, strength):
    """
    在指定位置(x, y)产生一个水滴
    radius: 半径
    strength: 波的初始高度
    """
    # 确保坐标在范围内
    if x < radius or x >= WIDTH - radius or y < radius or y >= HEIGHT - radius:
        return

    # 创建一个圆形区域的掩码
    Y, X = np.ogrid[:HEIGHT, :WIDTH]
    dist_from_center = np.sqrt((X - x) ** 2 + (Y - y) ** 2)

    # 在buffer1上施加力 (形成凹陷或凸起)
    mask = dist_from_center <= radius
    buffer1[mask.T] = strength


def update_physics():
    """
    核心波动算法 (使用Numpy切片加速)
    公式: New = (Prev[left] + Prev[right] + Prev[up] + Prev[down]) / 2 - Current
    """
    global buffer1, buffer2

    # 利用切片获取上下左右的邻居
    # 这种写法比双重for循环快几百倍
    # buffer1[1:-1, 1:-1] 代表除去边缘的中心区域

    # 计算周围四个点的平均值，乘以2 (算法优化变体)
    avg_neighbors = (
                            buffer1[0:-2, 1:-1] +  # Left
                            buffer1[2:, 1:-1] +  # Right
                            buffer1[1:-1, 0:-2] +  # Up
                            buffer1[1:-1, 2:]  # Down
                    ) / 2.0

    # 波动方程核心：下一帧状态 = 邻居影响 - 上上一帧状态
    buffer2[1:-1, 1:-1] = avg_neighbors - buffer2[1:-1, 1:-1]

    # 施加阻尼，让波纹逐渐消失
    buffer2 *= DAMPING

    # 交换缓冲区，buffer2 变成当前的，buffer1 变成旧的以便下次计算
    buffer1, buffer2 = buffer2, buffer1


def render_waves():
    """
    渲染逻辑：根据高度差计算折射偏移
    """
    # 计算X方向和Y方向的斜率 (作为折射偏移量)
    # diff_x = height[x+1] - height[x-1]
    offset_x = buffer1[2:, 1:-1] - buffer1[0:-2, 1:-1]
    offset_y = buffer1[1:-1, 2:] - buffer1[1:-1, 0:-2]

    # 裁剪到合适的大小 (因为切片导致边缘少了一圈)
    # 我们需要将 offset 映射回原图索引

    # 这是一个简化的折射映射，将 float 偏移量转为 int
    offset_x = offset_x.astype(np.int32)
    offset_y = offset_y.astype(np.int32)

    # 生成坐标网格
    grid_x, grid_y = np.indices((WIDTH - 2, HEIGHT - 2))

    # 应用偏移量
    render_x = grid_x + offset_x
    render_y = grid_y + offset_y

    # 边界限制 (防止索引越界)
    render_x = np.clip(render_x, 0, WIDTH - 1)
    render_y = np.clip(render_y, 0, HEIGHT - 1)

    # 使用高级索引从背景数组中取像素
    # 这一步实现了“看透水面”的效果
    pixels = bg_arr_source[render_x, render_y]

    # 将处理后的像素数组绘制到屏幕上
    # 这种方法比 pygame.PixelArray 快得多
    dest_surf = pygame.surfarray.make_surface(pixels)
    screen.blit(dest_surf, (1, 1))


# --- 主循环 ---
running = True
mouse_pressed = False
press_start_time = 0

print("程序已启动。在窗口任意位置点击并按住鼠标...")

while running:
    # 1. 事件处理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pressed = True
            press_start_time = time.time()

        elif event.type == pygame.MOUSEBUTTONUP:
            if mouse_pressed:
                mouse_pressed = False
                press_duration = time.time() - press_start_time

                # 映射逻辑：时间越长，半径越大，力度越深
                # 限制最大半径，防止太夸张
                radius = int(min(10 + press_duration * 100, 80))
                strength = -500 - (press_duration * 500)  # 负值表示向下压水面

                mx, my = pygame.mouse.get_pos()
                add_drop(mx, my, radius, strength)
                # print(f"Drop: Radius={radius}, Strength={strength:.2f}")

    # 2. 物理更新
    update_physics()

    # 3. 渲染
    # 为了性能，我们可以不每一帧都重新生成整个画面，
    # 但对于波纹这种全屏特效，重绘是必须的。
    # 先画背景 (其实 render_waves 已经包含了背景采样，这里可以省略直接覆盖)
    # screen.blit(background_surf, (0, 0))

    render_waves()

    # 显示当前FPS和提示
    pygame.display.set_caption(f"FPS: {clock.get_fps():.1f} | Hold Mouse to Resize Drop")
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()