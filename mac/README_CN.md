# Sophon Realtime Mac 版（Apple 芯片）

在 Mac 上**本地运行** Sophon-Realtime-32B-Flash-4bit，全双工对话：

- 可以随时打断它。
- 你说没说完，由模型自己判断。
- 它说话时你"嗯嗯"一下，它会接着讲。

听、判断话轮、说话都由模型自己在 Mac 的 GPU（MLX）上完成，不上云，中间也没有语音转文字这一步。

## 配置要求
- Apple 芯片（M1 及以后），macOS 14 及以上
- **推荐 36 GB 及以上统一内存**；32 GB 关掉其他程序也能跑（对话时模型约占 26 GB）
- 约 30 GB 空闲磁盘（模型约 24 GB）
- 麦克风：Mac Studio、Mac mini 没有内置麦克风，需要插 USB 麦克风或耳机。用外放没问题，已内置回音消除

## 安装（一条命令）
```bash
bash mac/install.sh
```
安装脚本会做这几件事：

- 在 `~/sophon-mac` 建独立的 Python 环境。
- 下载一次 [Sophon-Realtime-32B-Flash-4bit-MLX](https://modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Flash-4bit-MLX)（约 24 GB）：能连 Hugging Face 就从那里下，连不上自动改用魔搭和国内软件源。

这份权重就是 Flash-4bit 无损重新打包成的 MLX 格式。已经下载过显卡版 [Sophon-Realtime-32B-Flash-4bit](https://modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Flash-4bit) 的话，用 `convert.py 源目录 目标目录` 约 1 分钟就能转出同样的文件。

下载中断了，再运行一次安装命令即可续传。

## 开始对话
```bash
~/sophon-mac/sophon              # 中文
~/sophon-mac/sophon --lang en    # 英文
```
常用选项：

- `--no-aec`：关闭回音消除（戴耳机时用）
- `--in` / `--out`：选择音频设备，`--list` 列出所有设备
- `--voice`：选择音色

启动时加载模型约 10 秒。

## 速度（M4 Max，36 GB）
| | |
|---|---|
| 你说完 → 它开口 | 模型确定你说完了：**0.9–1.1 秒**；拿不准、要等等看你是否接着说：最长约 2.5 秒 |
| 长回复 | 实时，不卡顿 |
| 你打断它 | 约 0.15 秒内停下 |

服务器版约 0.5 秒出声。Mac 上最花时间的是话轮判断：模型要把你整段话在 Mac 的 GPU 上算一遍。GPU 核数更多的芯片（Max / Ultra）会更快。

## 工作方式
- 用户语音通过模型自己的音频塔直接进入模型。你一停顿，就在同一个上下文里问模型"说完了吗"。说完了就接着这次计算直接回复，所以整段音频只算一次。
- 话轮检查的时间点和阈值与服务器版相同：静音 0.2–2 秒间检查，到 2 秒兜底回复。
- 打断后回复立刻停止，对话历史里只保留实际说出口的部分。打断后紧接着的简短附和（"嗯嗯""对"）会让它从被打断处接着讲。
- 回音消除（WebRTC AEC3）把回复自己的声音从麦克风里去掉，外放时不会自己打断自己。

## 现状与限制
- 已在 M4 Max（36 GB）上测试，输入是实时模拟的音频（按真实速度把语音喂给引擎，并模拟房间回声）。欢迎在 [issue #1](https://github.com/adventists-ai/sophon-realtime/issues/1) 分享真实麦克风的使用体验和其他型号 Mac 的数据。
- 一次只能进行一路对话。Mac 版暂不支持摄像头输入、工具调用和零样本声音克隆（只有内置音色）。
