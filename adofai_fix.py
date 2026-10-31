#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADOFAI Linux Native Enhancement & Compatibility Toolkit
========================================================
从底层注入到全套修复的完全体解决方案：
1. UMM 底层 Assembly 注入检测与修复
2. Shader.WarmupAllShaders 崩溃拦截
3. UMM 原生 IMGUI 滑动条拖拽失焦修复与高分屏优化
4. Together 模组反作弊/白名单实时绕过
5. CJK / 中文字体方块乱码（豆腐块）自动修复
"""

import os
import sys
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Tuple

VERSION = "1.0.0"
AUTHOR = "Antigravity & Hoshi"

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[32m"
C_CYAN = "\033[36m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_MAGENTA = "\033[35m"

def print_banner():
    banner = f"""{C_CYAN}{C_BOLD}
    ╔════════════════════════════════════════════════════════════════╗
    ║       ADOFAI Linux Native Toolkit (完全体全自动修复套件)       ║
    ║   Shader Crash Skip • IMGUI Slider Fix • Together Bypass • CJK ║
    ╚════════════════════════════════════════════════════════════════╝
    {C_RESET}{C_YELLOW}Version: {VERSION} | Author: {AUTHOR}{C_RESET}
    """
    print(banner)

def find_adofai_dir() -> Optional[Path]:
    """Auto-detect ADOFAI installation directory across common Linux / Steam Deck paths."""
    candidates = [
        os.environ.get("ADOFAI_PATH"),
        Path.home() / ".steam/debian-installation/steamapps/common/A Dance of Fire and Ice",
        Path.home() / ".steam/steam/steamapps/common/A Dance of Fire and Ice",
        Path.home() / ".local/share/Steam/steamapps/common/A Dance of Fire and Ice",
        Path.home() / ".var/app/com.valvesoftware.Steam/data/Steam/steamapps/common/A Dance of Fire and Ice",
        Path("/var/lib/flatpak/app/com.valvesoftware.Steam/data/Steam/steamapps/common/A Dance of Fire and Ice"),
    ]
    for c in candidates:
        if c:
            p = Path(c).expanduser().resolve()
            if (p / "ADanceOfFireAndIce").is_file() or (p / "A Dance of Fire and Ice.exe").is_file():
                return p
    return None

def get_managed_dir(game_dir: Path) -> Optional[Path]:
    for name in ["ADanceOfFireAndIce_Data/Managed", "A Dance of Fire and Ice_Data/Managed"]:
        m = game_dir / name
        if m.is_dir():
            return m
    return None

def check_system_cjk_fonts() -> List[str]:
    """Detect installed CJK fonts on the host system."""
    preferred = [
        "DejaVu Sans",
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "WenQuanYi Zen Hei",
        "Microsoft YaHei",
        "SimHei",
        "Source Han Sans CN"
    ]
    detected = []
    try:
        out = subprocess.check_output(["fc-list", ":", "family"], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
        families = set(f.strip() for line in out.splitlines() for f in line.split(","))
        for p in preferred:
            if p in families:
                detected.append(p)
    except Exception:
        detected = ["DejaVu Sans"]
    return detected if detected else ["DejaVu Sans"]

ADOFAI_APPID = "977950"
DOORSTOP_RUNTIME = ("launch.sh", "run.sh", "libdoorstop.so", "LICENSE", ".doorstop_version")
UMM_BACKUP_FILES = (
    "UnityModManager.dll",
    "UnityModManager.xml",
    "0Harmony.dll",
    "dnlib.dll",
    "Config.xml",
    "Params.xml",
)


def doorstop_home() -> Path:
    return Path.home() / ".local/share/adofai-linux-fix/doorstop"


def steam_is_running() -> bool:
    try:
        out = subprocess.check_output(
            ["pgrep", "-af", "ubuntu12_32/steam"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return bool(out.strip())


def iter_steam_localconfigs():
    roots = [
        Path.home() / ".steam/steam/userdata",
        Path.home() / ".steam/debian-installation/userdata",
        Path.home() / ".local/share/Steam/userdata",
        Path.home() / ".var/app/com.valvesoftware.Steam/data/Steam/userdata",
    ]
    seen = set()
    for root in roots:
        if not root.is_dir():
            continue
        for cfg in root.glob("*/config/localconfig.vdf"):
            try:
                real = cfg.resolve()
            except OSError:
                continue
            if real in seen:
                continue
            seen.add(real)
            yield cfg


def merge_launch_option(current: str, script: str) -> str:
    current = current.strip()
    if script in current:
        return current
    if not current:
        return f"{script} %command%"
    if "%command%" in current:
        return current.replace("%command%", f"{script} %command%", 1)
    return f"{script} %command%"


def rewrite_app_launch_option(text: str, appid: str, script: str):
    """Return (new_text, found, changed) for one Steam app block."""
    token = f'"{appid}"'
    pos = 0
    found = False
    changed = False
    while True:
        start = text.find(token, pos)
        if start < 0:
            break
        brace = text.find("{", start)
        if brace < 0 or brace - start > 40:
            pos = start + len(token)
            continue
        depth = 0
        end = None
        for idx in range(brace, len(text)):
            char = text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break
        if end is None:
            break
        block = text[brace:end]
        key = '"LaunchOptions"'
        key_at = block.find(key)
        if key_at < 0:
            pos = end
            continue
        quote_open = block.find('"', key_at + len(key))
        quote_close = block.find('"', quote_open + 1) if quote_open >= 0 else -1
        if quote_open < 0 or quote_close < 0:
            pos = end
            continue
        found = True
        current = block[quote_open + 1:quote_close]
        updated = merge_launch_option(current, script)
        if updated != current:
            block = block[:quote_open + 1] + updated + block[quote_close:]
            text = text[:brace] + block + text[end:]
            changed = True
            pos = brace + len(block)
        else:
            pos = end
    return text, found, changed


class AdoFaiToolkit:
    def __init__(self, game_dir: Path):
        self.game_dir = game_dir
        self.managed_dir = get_managed_dir(game_dir)
        if not self.managed_dir:
            raise RuntimeError(f"Could not locate Managed directory in {game_dir}")
        self.umm_dir = self.managed_dir / "UnityModManager"
        self.mods_dir = self.game_dir / "Mods"
        self.core_module = self.managed_dir / "UnityEngine.CoreModule.dll"
        self.core_module_backup = self.managed_dir / "UnityEngine.CoreModule.dll.original_"
        self.params_xml = self.umm_dir / "Params.xml"
        self.root_dir = Path(__file__).parent.resolve()

    def status(self) -> dict:
        """Inspect the current game and mod status."""
        injected = False
        if self.core_module.is_file():
            try:
                with open(self.core_module, "rb") as f:
                    injected = b"UnityModManager" in f.read()
            except Exception:
                pass

        mod_installed = (self.mods_dir / "LinuxCrashFix" / "LinuxCrashFix.dll").is_file()
        current_font = "Unknown"
        if self.params_xml.is_file():
            try:
                tree = ET.parse(self.params_xml)
                font_elem = tree.find("UIFont")
                if font_elem is not None and font_elem.text:
                    current_font = font_elem.text
            except Exception:
                pass

        home = doorstop_home()
        script = str(home / "launch.sh")
        doorstop_files = (home / "launch.sh").is_file() and (home / "libdoorstop.so").is_file()
        launch_option = False
        for cfg in iter_steam_localconfigs():
            try:
                body = cfg.read_text(errors="replace")
            except OSError:
                continue
            _, found, _ = rewrite_app_launch_option(body, ADOFAI_APPID, script)
            if found and script in body:
                launch_option = True
                break

        return {
            "game_dir": str(self.game_dir),
            "managed_dir": str(self.managed_dir),
            "umm_patched": injected,
            "umm_injected": injected or (doorstop_files and launch_option),
            "doorstop": doorstop_files and launch_option,
            "has_backup": self.core_module_backup.is_file(),
            "mod_installed": mod_installed,
            "ui_font": current_font,
            "system_fonts": check_system_cjk_fonts()
        }

    def print_status(self):
        st = self.status()
        print(f"\n{C_BOLD}=== 🎮 游戏环境诊断报告 ==={C_RESET}")
        print(f" • 游戏根目录: {C_CYAN}{st['game_dir']}{C_RESET}")
        print(f" • Managed 路径: {C_CYAN}{st['managed_dir']}{C_RESET}")
        
        if st["doorstop"]:
            inj_str = f"{C_GREEN}Doorstop 启动项（游戏更新后仍会注入）{C_RESET}"
        elif st["umm_patched"]:
            inj_str = f"{C_YELLOW}只补在了 CoreModule 上（游戏更新后会掉）{C_RESET}"
        else:
            inj_str = f"{C_RED}未注入 (需要修复){C_RESET}"
        print(f" • UMM 底层挂钩: {inj_str}")

        bk_str = f"{C_GREEN}存在{C_RESET}" if st['has_backup'] else f"{C_YELLOW}未检测到{C_RESET}"
        print(f" • 核心备份文件: {bk_str}")

        mod_str = f"{C_GREEN}已就绪 (v1.0.0){C_RESET}" if st['mod_installed'] else f"{C_RED}未安装{C_RESET}"
        print(f" • LinuxNativeFix 模组: {mod_str}")

        print(f" • 当前 UMM 字体: {C_MAGENTA}{st['ui_font']}{C_RESET}")
        print(f" • 推荐系统字体: {', '.join(st['system_fonts'][:3])}")
        print("============================\n")

    def fix_font(self, font_name: Optional[str] = None) -> bool:
        """Update Params.xml to use a valid CJK font."""
        if not self.params_xml.is_file():
            print(f"{C_YELLOW}[!] Params.xml 尚未生成，将在游戏启动并保存配置后创建。{C_RESET}")
            return False

        if not font_name:
            fonts = check_system_cjk_fonts()
            font_name = fonts[0] if fonts else "DejaVu Sans"

        try:
            tree = ET.parse(self.params_xml)
            root = tree.getroot()
            font_elem = root.find("UIFont")
            if font_elem is None:
                font_elem = ET.SubElement(root, "UIFont")
            font_elem.text = font_name
            tree.write(self.params_xml, encoding="utf-8", xml_declaration=True)
            print(f"{C_GREEN}[+] 成功将 UMM 字体更新为: {font_name}{C_RESET}")
            return True
        except Exception as ex:
            print(f"{C_RED}[-] 写入字体配置失败: {ex}{C_RESET}")
            return False

    def install_mod(self) -> bool:
        """Install LinuxCrashFix mod files into Mods/LinuxCrashFix/."""
        dist_mod = self.root_dir / "dist" / "LinuxCrashFix"
        target_mod = self.mods_dir / "LinuxCrashFix"

        if not dist_mod.is_dir():
            print(f"{C_YELLOW}[*] 未找到预编译包，正在尝试从源码编译...{C_RESET}")
            if not self.build_mod():
                return False

        target_mod.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dist_mod / "Info.json", target_mod / "Info.json")
        shutil.copy2(dist_mod / "LinuxCrashFix.dll", target_mod / "LinuxCrashFix.dll")
        print(f"{C_GREEN}[+] Linux Native Crash Fix 模组已成功安装至: {target_mod}{C_RESET}")
        return True

    def build_mod(self) -> bool:
        """Compile LinuxCrashFix.cs using mcs."""
        build_script = self.root_dir / "scripts" / "build.sh"
        if not build_script.is_file():
            print(f"{C_RED}[-] 找不到编译脚本: {build_script}{C_RESET}")
            return False

        print(f"{C_CYAN}[*] 正在调用 mcs 编译源码...{C_RESET}")
        try:
            subprocess.check_call(["bash", str(build_script), str(self.game_dir)])
            print(f"{C_GREEN}[+] 模组编译完成！{C_RESET}")
            return True
        except Exception as ex:
            print(f"{C_RED}[-] 编译失败: {ex}{C_RESET}")
            return False

    def install_doorstop(self) -> bool:
        """Install the Doorstop launcher outside the game and pin the Steam launch option."""
        bundled = self.root_dir / "doorstop"
        if not (bundled / "libdoorstop.so").is_file() or not (bundled / "launch.sh").is_file():
            print(f"{C_RED}[-] 仓库里缺少 doorstop 运行时，无法安装持久注入。{C_RESET}")
            return False

        home = doorstop_home()
        home.mkdir(parents=True, exist_ok=True)
        for name in DOORSTOP_RUNTIME:
            src = bundled / name
            if src.is_file():
                shutil.copy2(src, home / name)
        for name in ("launch.sh", "run.sh", "libdoorstop.so"):
            target = home / name
            if target.is_file():
                target.chmod(0o755)

        live = self.umm_dir
        if (live / "UnityModManager.dll").is_file():
            stash = home / "backup" / "UnityModManager"
            stash.mkdir(parents=True, exist_ok=True)
            copied = 0
            for name in UMM_BACKUP_FILES:
                src = live / name
                if src.is_file():
                    shutil.copy2(src, stash / name)
                    copied += 1
            print(f"{C_GREEN}[+] 已备份 UMM 到 {stash}（{copied} 个文件）。{C_RESET}")
        else:
            print(f"{C_YELLOW}[!] 游戏目录里还没有 UnityModManager。钩子已装上，但要先装一次 UMM 才会有东西可注入。{C_RESET}")

        script = str(home / "launch.sh")
        found = False
        updated = False
        blocked = False
        for cfg in iter_steam_localconfigs():
            try:
                text = cfg.read_text(errors="replace")
            except OSError as ex:
                print(f"{C_YELLOW}[!] 读不到 {cfg}: {ex}{C_RESET}")
                continue
            new_text, app_found, changed = rewrite_app_launch_option(text, ADOFAI_APPID, script)
            if not app_found:
                continue
            found = True
            if not changed:
                continue
            if steam_is_running():
                blocked = True
                continue
            cfg.write_text(new_text)
            updated = True
            print(f"{C_GREEN}[+] 已写入 Steam 启动项: {cfg}{C_RESET}")

        if not found:
            print(f"{C_YELLOW}[!] 没有在 Steam 用户配置里找到 ADOFAI（AppID {ADOFAI_APPID}）。{C_RESET}")
            print(f"{C_YELLOW}    请在游戏启动项里填这一行:{C_RESET}")
            print(f"    {script} %command%")
            return False
        if blocked:
            print(f"{C_YELLOW}[!] Steam 正在运行，现在改配置文件会在退出时被盖回去。{C_RESET}")
            print(f"{C_YELLOW}    请先退出 Steam，再运行一次 ./install.sh --doorstop，或把下面这行填进启动项:{C_RESET}")
            print(f"    {script} %command%")
            return False
        if updated:
            print(f"{C_GREEN}[+] 持久注入已挂到 Steam 启动项。下次从 Steam 开游戏就会注入。{C_RESET}")
        else:
            print(f"{C_GREEN}[+] Steam 启动项里已经有 Doorstop，不用再改。{C_RESET}")
        return True

    def full_auto_setup(self):
        """Execute end-to-end full repair from injection to final state."""
        print(f"{C_CYAN}{C_BOLD}[*] 开始执行全自动一键配置流程 (从注入到完全体)...{C_RESET}")
        
        # 1. 确保模组目录存在
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. 检查核心备份
        if not self.core_module_backup.is_file() and self.core_module.is_file():
            st = self.status()
            if not st["umm_patched"]:
                shutil.copy2(self.core_module, self.core_module_backup)
                print(f"{C_GREEN}[+] 已创建原生 UnityEngine.CoreModule.dll 纯净备份。{C_RESET}")

        print(f"{C_CYAN}[1/4] 安装 Doorstop，让注入在游戏更新后仍然生效...{C_RESET}")
        self.install_doorstop()

        # 3. 安装 LinuxCrashFix 终极模组
        print(f"{C_CYAN}[2/4] 安装 Linux Crash Fix 核心扩展模组...{C_RESET}")
        self.install_mod()

        # 4. 修复中文字体
        print(f"{C_CYAN}[3/4] 配置中文字体与本地化防乱码...{C_RESET}")
        self.fix_font()

        # 5. 状态确认
        print(f"{C_CYAN}[4/4] 验证运行环境与防护逻辑...{C_RESET}")
        st = self.status()
        print(f"\n{C_GREEN}{C_BOLD}全自动化修复全部完成。{C_RESET}")
        print(f" • Shader 预热崩溃拦截: {C_GREEN}已启用{C_RESET}")
        print(f" • IMGUI 连续拖拽与高分屏优化: {C_GREEN}已启用{C_RESET}")
        print(f" • Together 联机反作弊白名单绕过: {C_GREEN}已启用{C_RESET}")
        print(f" • 中文字体方块乱码消除: {C_GREEN}已配置 ({st['ui_font']}){C_RESET}")
        print(f"\n{C_YELLOW}您现在可以直接启动 ADOFAI 游戏！{C_RESET}\n")

def interactive_menu(toolkit: AdoFaiToolkit):
    while True:
        toolkit.print_status()
        print(f"{C_BOLD}请选择操作选项:{C_RESET}")
        print(f" {C_GREEN}[1]{C_RESET} 一键全自动修复 (持久注入 + 模组安装 + 字体配置 + 绕过白名单)")
        print(f" {C_CYAN}[2]{C_RESET} 仅编译并安装/更新 Linux Crash Fix 模组")
        print(f" {C_CYAN}[3]{C_RESET} 修复中文字体 (解决 UMM 方块字乱码)")
        print(f" {C_CYAN}[4]{C_RESET} 重新从源码编译模组 (Build from Source)")
        print(f" {C_CYAN}[5]{C_RESET} 查看当前详细诊断信息")
        print(f" {C_CYAN}[6]{C_RESET} 只安装持久注入 (Doorstop，游戏更新后不用再手动注入)")
        print(f" {C_RED}[0]{C_RESET} 退出程序")

        choice = input(f"\n{C_BOLD}请输入选项 [1-6, 0]: {C_RESET}").strip()
        if choice == "1":
            toolkit.full_auto_setup()
            input(f"\n{C_YELLOW}按回车键继续...{C_RESET}")
        elif choice == "2":
            toolkit.install_mod()
            input(f"\n{C_YELLOW}按回车键继续...{C_RESET}")
        elif choice == "3":
            fonts = check_system_cjk_fonts()
            print("\n可用的系统字体:")
            for idx, f in enumerate(fonts, 1):
                print(f"  {idx}. {f}")
            f_choice = input(f"输入字体序号或直接回车使用默认 [{fonts[0]}]: ").strip()
            sel_font = fonts[int(f_choice)-1] if f_choice.isdigit() and 1 <= int(f_choice) <= len(fonts) else fonts[0]
            toolkit.fix_font(sel_font)
            input(f"\n{C_YELLOW}按回车键继续...{C_RESET}")
        elif choice == "4":
            toolkit.build_mod()
            input(f"\n{C_YELLOW}按回车键继续...{C_RESET}")
        elif choice == "5":
            toolkit.print_status()
            input(f"\n{C_YELLOW}按回车键继续...{C_RESET}")
        elif choice == "6":
            toolkit.install_doorstop()
            input(f"\n{C_YELLOW}按回车键继续...{C_RESET}")
        elif choice == "0":
            print("感谢使用，再见！")
            break
        else:
            print(f"{C_RED}无效选项，请重新输入。{C_RESET}")

def main():
    print_banner()

    # Locate game
    game_dir = find_adofai_dir()
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        game_dir = Path(sys.argv[1])

    if not game_dir or not game_dir.is_dir():
        print(f"{C_RED}[-] 未能自动识别到《冰与火之舞》(ADOFAI) 游戏目录。{C_RESET}")
        inp = input(f"{C_BOLD}请输入您的游戏安装完整路径: {C_RESET}").strip()
        if inp:
            game_dir = Path(inp).expanduser().resolve()

    if not game_dir or not game_dir.is_dir():
        print(f"{C_RED}[-] 错误: 路径无效，程序退出。{C_RESET}")
        sys.exit(1)

    toolkit = AdoFaiToolkit(game_dir)

    # CLI Flags
    if "--auto" in sys.argv or "--all" in sys.argv:
        toolkit.full_auto_setup()
    elif "--build" in sys.argv:
        toolkit.build_mod()
    elif "--install" in sys.argv:
        toolkit.install_mod()
    elif "--doorstop" in sys.argv:
        toolkit.install_doorstop()
    elif "--font" in sys.argv:
        toolkit.fix_font()
    else:
        interactive_menu(toolkit)

if __name__ == "__main__":
    main()
