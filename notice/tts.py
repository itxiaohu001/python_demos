import pyttsx3
import sys

def speak_text(text, voice_id=None, rate=150, volume=1.0):
    """
    使用指定的语音朗读文本
    
    参数:
    text (str): 要朗读的文本
    voice_id (str, 可选): 语音ID，如果为None则使用默认语音
    rate (int): 语速 (默认150)
    volume (float): 音量 0.0-1.0 (默认1.0)
    """
    # 初始化语音引擎
    engine = pyttsx3.init()
    
    # 设置语速和音量
    engine.setProperty('rate', rate)
    engine.setProperty('volume', volume)
    
    # 获取可用的语音
    voices = engine.getProperty('voices')
    
    # 如果指定了voice_id, 设置语音
    if voice_id is not None:
        try:
            voice_id = int(voice_id)
            if 0 <= voice_id < len(voices):
                engine.setProperty('voice', voices[voice_id].id)
            else:
                print(f"错误: 语音ID {voice_id} 超出范围 (0-{len(voices)-1})")
                list_voices(engine)
                return
        except ValueError:
            # 如果voice_id不是数字，尝试通过名称匹配
            found = False
            for i, voice in enumerate(voices):
                if voice_id.lower() in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    found = True
                    break
            if not found:
                print(f"错误: 找不到语音 '{voice_id}'")
                list_voices(engine)
                return
    
    # 朗读文本
    engine.say(text)
    engine.runAndWait()

def list_voices(engine=None):
    """列出所有可用的语音"""
    if engine is None:
        engine = pyttsx3.init()
    
    voices = engine.getProperty('voices')
    print("\n可用语音:")
    print("-" * 60)
    print(f"{'ID':<4} | {'名称':<40} | {'语言':<10}")
    print("-" * 60)
    
    for i, voice in enumerate(voices):
        lang = voice.languages[0] if voice.languages else "未知"
        print(f"{i:<4} | {voice.name:<40} | {lang:<10}")

def main():
    # 如果没有命令行参数，显示使用说明
    if len(sys.argv) == 1:
        print("\n文本转语音程序")
        print("\n使用方法:")
        print("1. 列出所有可用语音:")
        print("   python tts.py --list-voices")
        print("\n2. 朗读文本:")
        print("   python tts.py \"要朗读的文本\"")
        print("\n3. 使用特定语音朗读文本:")
        print("   python tts.py \"要朗读的文本\" --voice=0")
        print("\n4. 调整语速和音量:")
        print("   python tts.py \"要朗读的文本\" --voice=0 --rate=150 --volume=0.8")
        print("\n选项:")
        print("   --voice=ID     选择语音 (ID或名称的一部分)")
        print("   --rate=RATE    语速 (默认150, 范围通常为50-300)")
        print("   --volume=VOL   音量 (默认1.0, 范围0.0-1.0)")
        return

    # 解析命令行参数
    if "--list-voices" in sys.argv:
        list_voices()
        return
    
    # 获取文本
    text = None
    voice_id = None
    rate = 150
    volume = 1.0
    
    for arg in sys.argv[1:]:
        if arg.startswith("--voice="):
            voice_id = arg[8:]
        elif arg.startswith("--rate="):
            try:
                rate = int(arg[7:])
            except ValueError:
                print(f"错误: 语速必须是整数")
                return
        elif arg.startswith("--volume="):
            try:
                volume = float(arg[9:])
                if not 0.0 <= volume <= 1.0:
                    print("错误: 音量必须在0.0至1.0之间")
                    return
            except ValueError:
                print(f"错误: 音量必须是浮点数")
                return
        elif text is None and not arg.startswith("--"):
            text = arg
    
    if text is None:
        print("错误: 请提供要朗读的文本")
        return
    
    # 朗读文本
    speak_text(text, voice_id, rate, volume)

# 交互式界面
def interactive_mode():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    print("\n====== 文本转语音交互程序 ======")
    list_voices(engine)
    
    current_voice = 0
    rate = 150
    volume = 1.0
    
    while True:
        print("\n" + "=" * 40)
        print(f"当前设置:")
        print(f"- 语音: {current_voice} ({voices[current_voice].name})")
        print(f"- 语速: {rate}")
        print(f"- 音量: {volume}")
        
        print("\n命令:")
        print("- 输入文本朗读")
        print("- voice <ID> 切换语音")
        print("- rate <值> 调整语速")
        print("- volume <值> 调整音量")
        print("- list 显示所有语音")
        print("- exit 退出程序")
        
        cmd = input("\n> ")
        
        if cmd.lower() == "exit":
            break
        elif cmd.lower() == "list":
            list_voices(engine)
        elif cmd.lower().startswith("voice "):
            try:
                voice_id = int(cmd[6:])
                if 0 <= voice_id < len(voices):
                    current_voice = voice_id
                    engine.setProperty('voice', voices[current_voice].id)
                else:
                    print(f"错误: 语音ID超出范围 (0-{len(voices)-1})")
            except ValueError:
                print("错误: 语音ID必须是整数")
        elif cmd.lower().startswith("rate "):
            try:
                rate = int(cmd[5:])
                engine.setProperty('rate', rate)
            except ValueError:
                print("错误: 语速必须是整数")
        elif cmd.lower().startswith("volume "):
            try:
                volume = float(cmd[7:])
                if 0.0 <= volume <= 1.0:
                    engine.setProperty('volume', volume)
                else:
                    print("错误: 音量必须在0.0至1.0之间")
            except ValueError:
                print("错误: 音量必须是浮点数")
        else:
            # 将输入视为要朗读的文本
            engine.say(cmd)
            engine.runAndWait()

if __name__ == "__main__":
    # 如果带有--interactive参数，启动交互模式
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        main()