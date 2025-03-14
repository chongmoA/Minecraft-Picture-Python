import os
import sys
import time
import math
from PIL import Image

from mcpi.minecraft import Minecraft
import mcpi.block as block

# 用来采样颜色的图片文件夹路径
SAMPLE_FOLDER = r""
# 颜色采样字典，(r,g,b) 作为键，(材质ID, 子材质序号) 作为值
dictSampleColor = dict()
# 256色到材质的映射字典
dictColor256ToMaterail = dict()

# 读取全部图片，生成颜色查找表
def loadColorMap(folderPath):
    try:
        # 获取文件夹中的所有文件名
        lstFileName = os.listdir(folderPath)
        for fileName in lstFileName:
            fullPath = os.path.join(folderPath, fileName)
            if os.path.isfile(fullPath):
                _loadFile(fullPath)

        # 对256色中的每一种，指定一个材质
        # 256色模式： 共8 bits (R: 3 bits; G: 3 bits; B: 2 bits)
        for r in range(8):
            for g in range(8):
                for b in range(4):
                    value = _findNearestByRgb(r, g, b)
                    key = (r, g, b)
                    dictColor256ToMaterail[key] = value
    except Exception as e:
        print(f"加载颜色映射时出错: {e}")

# 加载单个图片文件
def _loadFile(fullPath):
    try:
        im = Image.open(fullPath)
        # 计算key值(r,g,b)
        r, g, b = _calAverageRgb(im)
        r >>= 5; g >>= 5; b >>= 6

        # 文件名中包含id和序号，如 35-2
        fileName = fullPath.split(os.sep)[-1][:-4]

        # 改为turtle (35,2)的形式
        arr = fileName.split('-')
        tt = (int(arr[0]), int(arr[1]))

        # 放入词典，样式：{(r, g, b), (材质ID, 子材质序号)}
        dictSampleColor[(r, g, b)] = tt
    except Exception as e:
        print(f"加载文件 {fullPath} 时出错: {e}")

# 计算两个RGB颜色之间的距离（LAB颜色空间）
def _colorDistance(rgb1, rgb2):
    R_1, G_1, B_1 = rgb1
    R_2, G_2, B_2 = rgb2
    rmean = (R_1 + R_2) / 2
    R = R_1 - R_2
    G = G_1 - G_2
    B = B_1 - B_2

    return math.sqrt((2 + rmean / 256) * (R ** 2) + 4 * (G ** 2) + (2 + (255 - rmean) / 256) * (B ** 2))

# 计算图片的平均RGB值
def _calAverageRgb(im):
    if im.mode != "RGB":
        im = im.convert("RGB")

    pix = im.load()
    avgR, avgG, avgB = 0, 0, 0
    n = 1
    for i in range(im.size[0]):
        for j in range(im.size[1]):
            r, g, b = pix[i, j]
            avgR += r
            avgG += g
            avgB += b
            n += 1

    return (avgR // n, avgG // n, avgB // n)

# 获取颜色最接近的方块
def _findNearestByRgb(r, g, b):
    minError = 3 * 255 * 255  # 初值为最大误差
    k = ""
    for key in dictSampleColor.keys():
        R, G, B = key
        # 计算颜色误差，用平方差的和来表示
        cur_dif = _colorDistance((r, g, b), (R, G, B))
        if cur_dif < minError:
            minError = cur_dif
            k = key

    return dictSampleColor[k]

# 初始化函数
def init():
    global mc, x, y, z
    try:
        print('加载颜色样图...')
        loadColorMap(SAMPLE_FOLDER)

        print('连接MC...')
        mc = Minecraft.create()
        x, y, z = mc.player.getTilePos()
    except Exception as e:
        print(f"初始化时出错: {e}")

# 绘制图片帧
def drawFrame(img, direction, is_mirrored, flip_up_down, flip_left_right):
    try:
        imgW, imgH = img.size

        if flip_up_down:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        if flip_left_right:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

        zDistance = (imgW * 100) // 256

        for row in range(imgH):
            for col in range(imgW):
                if is_mirrored:
                    col = imgW - 1 - col

                # img中每个点的颜色分量
                r, g, b, alpha = img.getpixel((col, row))

                # 256色模式中，r:g:b = 3:3:2 bits
                r >>= 5; g >>= 5; b >>= 6

                # 搜索最匹配图片
                if alpha == 0:
                    # 如果png图片在此位置的透明度是0，画个空气（寂寞）
                    materialID, subIndex = (block.AIR.id, 0)
                else:
                    materialID, subIndex = dictColor256ToMaterail[(r, g, b)]

                if direction == 'x':
                    mc.setBlock(x + col, y, z + (imgH / 2 - row), materialID, subIndex)
                elif direction == 'z':
                    mc.setBlock(x + (imgW / 2 - col), y, z + row, materialID, subIndex)
                elif direction == 'y':
                    mc.setBlock(x + (imgW / 2 - col), y + row, z, materialID, subIndex)

            time.sleep(0.05)
    except Exception as e:
        print(f"绘制图片时出错: {e}")

# 入口
if __name__ == '__main__':
    print("示例代码，简洁起见，必须使用png格式图片")
    time.sleep(5)
    init()

    # 询问生成方向
    while True:
        direction = input("请选择像素画生成方向 (x/z/y): ").lower()
        if direction in ['x', 'z', 'y']:
            break
        else:
            print("无效的输入，请输入 x, z 或 y。")

    # 询问是否镜像
    while True:
        mirror_input = input("是否生成镜像图像? (y/n): ").lower()
        if mirror_input in ['y', 'n']:
            is_mirrored = mirror_input == 'y'
            break
        else:
            print("无效的输入，请输入 y 或 n。")

    # 询问是否需要翻转
    while True:
        flip_input = input("是否需要对像素画进行上下或左右翻转? (y/n): ").lower()
        if flip_input in ['y', 'n']:
            if flip_input == 'y':
                # 询问是否上下翻转
                while True:
                    up_down_input = input("是否进行上下翻转? (y/n): ").lower()
                    if up_down_input in ['y', 'n']:
                        flip_up_down = up_down_input == 'y'
                        break
                    else:
                        print("无效的输入，请输入 y 或 n。")

                # 询问是否左右翻转
                while True:
                    left_right_input = input("是否进行左右翻转? (y/n): ").lower()
                    if left_right_input in ['y', 'n']:
                        flip_left_right = left_right_input == 'y'
                        break
                    else:
                        print("无效的输入，请输入 y 或 n。")
            else:
                flip_up_down = False
                flip_left_right = False
            break
        else:
            print("无效的输入，请输入 y 或 n。")

    try:
        # 确保 miku.png 文件存在于当前工作目录，或者指定完整路径
        img_path = os.path.join("example image.png")
        img = Image.open(img_path)
        drawFrame(img, direction, is_mirrored, flip_up_down, flip_left_right)
        print("绘制完成，等待mc刷新...")
    except FileNotFoundError:
        print(f"未找到文件: {img_path}，请检查路径是否正确")
    except Exception as e:
        print(f"运行时出错: {e}")
