# 免费零成本真人数字人 — Google Colab 预生成方案
# 
# 步骤：
# 1. 打开 https://colab.research.google.com
# 2. 新建笔记本，粘贴下面代码
# 3. 上传保险客服正面照（放到 /content/portrait.jpg）
# 4. 依次运行代码块，生成 5 段真人级数字人视频
# 5. 下载 .webm 文件，替换到项目的 web/public/avatar-videos/

# ======================== 代码块 1：安装依赖 ========================
# 耗时约 2 分钟
#
# !pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
# !pip install -q opencv-python face-alignment scipy
# !pip install -q edge-tts numpy
# !git clone https://github.com/Rudrabha/Wav2Lip
# !wget -q "https://iiitaphyd-my.sharepoint.com/personal/radrabha_m_research_iiit_ac_in/_layouts/15/download.aspx?share=EdjI7bZlgApMqsVoEUUXpLsBxqXbn5z8VTmoxp55YNDcIA" -O Wav2Lip/checkpoints/wav2lip_gan.pth
# !wget -q "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth" -O Wav2Lip/face_detection/detection/sfd/s3fd.pth

# ======================== 代码块 2：生成边缘 TTS 音频 ========================
# 
# import asyncio, edge_tts, os, subprocess
#
# ANSWERS = {
#   "greeting": "您好！我是智能保险客服，欢迎您。请问投保流程、理赔流程、退保规则、续保政策，你想了解哪方面？",
#   "claim": "理赔流程：第一步，拨打95511报案。第二步，准备身份证、保单、医疗记录。第三步，提交审核，三到五个工作日内完成。第四步，赔付金额到账。",
#   "insurance": "投保流程：第一步，选择产品，包括寿险、健康险、意外险、车险。第二步，填写个人信息。第三步，健康告知。第四步，支付保费。第五步，保单生效。二十四小时在线投保。",
#   "refund": "退保规则：投保后的十天犹豫期内，可以全额退款。超过犹豫期后，按照现金价值进行返还。办理退保需要准备保单、身份证和银行卡。",
#   "renewal": "续保政策：保障到期前的三十天内，可以办理续保手续。续保不需要重新核保，按照原费率或者调整后的费率计算即可。"
# }
#
# async def gen_tts():
#   os.makedirs("/content/audio", exist_ok=True)
#   for name, text in ANSWERS.items():
#     path = f"/content/audio/{name}.mp3"
#     comm = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
#     await comm.save(path)
#     print(f"  {name}.mp3 完成")
#
# await gen_tts()

# ======================== 代码块 3：Wav2Lip 生成视频 ========================
#
# 对每段音频生成口型同步视频
#
# import subprocess, os
# os.makedirs("/content/output", exist_ok=True)
#
# for name in ["greeting", "claim", "insurance", "refund", "renewal"]:
#   print(f"生成 {name}...")
#   subprocess.run([
#     "python", "Wav2Lip/inference.py",
#     "--checkpoint_path", "Wav2Lip/checkpoints/wav2lip_gan.pth",
#     "--face", "/content/portrait.jpg",
#     "--audio", f"/content/audio/{name}.mp3",
#     "--outfile", f"/content/output/{name}.mp4",
#     "--pads", "0", "10", "0", "0",
#     "--resize_factor", "1"
#   ])
#   print(f"  {name}.mp4 完成")

# ======================== 代码块 4：转 WebM + 下载 ========================
#
# import subprocess, os
# for name in ["greeting", "claim", "insurance", "refund", "renewal"]:
#   outname = "greeting" if name == "greeting" else name.replace("claim","claim-guide").replace("insurance","insurance-intro").replace("refund","refund-info").replace("renewal","renewal-info")
#   subprocess.run([
#     "ffmpeg", "-i", f"/content/output/{name}.mp4",
#     "-c:v", "libvpx", "-b:v", "500k", "-c:a", "libvorbis",
#     "-vf", "scale=640:480",
#     f"/content/output/{outname}.webm"
#   ])
#   print(f"  {outname}.webm 完成")
#
# from google.colab import files
# for name in ["greeting","claim-guide","insurance-intro","refund-info","renewal-info"]:
#   files.download(f"/content/output/{name}.webm")

# ======================== 代码块 5：真人视频替代方案（如果不想跑Wav2Lip）========================
# 
# 更简单的方案：直接用边缘TTS生成音频 + 静态照片做视频
# 效果不如Wav2Lip但生成极快（几秒钟）
#
# import subprocess, os
# ffmpeg_path = "ffmpeg"  # Colab 自带 ffmpeg
# for name in ["greeting","claim","insurance","refund","renewal"]:
#   outname = "greeting" if name == "greeting" else name.replace("claim","claim-guide").replace("insurance","insurance-intro").replace("refund","refund-info").replace("renewal","renewal-info")
#   subprocess.run([
#     ffmpeg_path, "-loop", "1", "-i", "/content/portrait.jpg",
#     "-i", f"/content/audio/{name}.mp3",
#     "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
#     "-shortest", "-pix_fmt", "yuv420p",
#     f"/content/output/{outname}.mp4"
#   ])

# ======================== 操作流程 ========================
# 1. 打开 colab.research.google.com
# 2. 左上角菜单 → 运行时 → 更改运行时类型 → GPU (T4)
# 3. 上传照片：左侧文件图标 → 上传 → portrait.jpg
# 4. 逐个运行上面的代码块（按播放按钮）
# 5. 最后一步会自动下载 5 个 .webm 文件
# 6. 把 .webm 放到项目 web/public/avatar-videos/ 目录
# 7. 效果：Wav2Lip 生成的真人级口型同步视频 + 边缘TTS语音
#
# 总耗时：约 10-15 分钟（主要是模型下载时间）
# 费用：¥0（完全免费）
# GPU：T4 (16GB VRAM) — 足够运行 Wav2Lip
