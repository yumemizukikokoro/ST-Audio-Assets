# -*- coding: utf-8 -*-
"""
ST-Audio-Assets 仓库维护脚本：
1. 重新生成 tree.txt（纯 tree /F /A 格式，UTF-8 编码，排除 .git）
2. 根据 SFX/ 与 Ambience/ 目录生成 siren_sfx_list_YYYYMMDD.json
   和 siren_ambience_list_YYYYMMDD.json
"""

import ctypes
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent
REPO_NAME = "yumemizukikokoro/ST-Audio-Assets"
BRANCH = "main"
BASE_URL = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}"
EXCLUDE_DIRS = {".git"}
AUDIO_EXT = ".ogg"


def get_volume_serial(root: Path) -> str:
    """获取盘符序列号，格式 XXXX-XXXX；失败时返回占位值。"""
    try:
        kernel32 = ctypes.windll.kernel32
        serial = ctypes.c_ulong(0)
        root_str = str(root.drive) + "\\"
        if kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root_str), None, 0,
            ctypes.byref(serial), None, None, None, 0,
        ):
            return f"{serial.value & 0xFFFF:04X}-{serial.value >> 16:04X}"
    except Exception:
        pass
    return "0000-0000"


def list_entries(dir_path: Path):
    """返回 (子目录列表, 文件列表)，均按名称排序。"""
    dirs, files = [], []
    for entry in dir_path.iterdir():
        if entry.name in EXCLUDE_DIRS:
            continue
        if entry.is_dir():
            dirs.append(entry)
        else:
            files.append(entry)
    dirs.sort(key=lambda p: p.name)
    files.sort(key=lambda p: p.name)
    return dirs, files


def build_tree_lines(root: Path):
    """生成与 `tree /F /A` 一致的行列表。"""
    lines = ["文件夹 PATH 列表",
             f"卷序列号为 {get_volume_serial(root)}",
             f"{root.drive}."]

    def emit(dir_path: Path, prefix: str, is_last: bool):
        dirs, files = list_entries(dir_path)
        # 文件行前缀：父级连接线 +（本目录若是最后一个子目录则对齐空格，否则竖线）
        file_prefix = prefix + ("    " if is_last else "|   ")
        for f in files:
            lines.append(file_prefix + f.name)
        if files and dirs:
            lines.append(file_prefix)
        for i, d in enumerate(dirs):
            last = (i == len(dirs) - 1)
            conn = "\\---" if last else "+---"
            lines.append(prefix + conn + d.name)
            emit(d, prefix + ("    " if last else "|   "), last)

    emit(root, "", False)
    return lines


def update_tree_txt():
    lines = build_tree_lines(REPO)
    out = REPO / "tree.txt"
    out.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(f"[tree] 已写入 {out}（{len(lines)} 行，UTF-8）")


def collect_audio(subdir: Path):
    """递归收集子目录下所有 .ogg，返回 (相对路径列表, 条目字典列表)。"""
    items = []
    if not subdir.is_dir():
        return items
    for path in sorted(subdir.rglob(f"*{AUDIO_EXT}")):
        rel = path.relative_to(REPO).as_posix()
        items.append({
            "name": path.stem,
            "url": f"{BASE_URL}/{rel}",
        })
    return items


def write_json(items: list, out_path: Path):
    with out_path.open("w", encoding="utf-8", newline="\n") as fp:
        json.dump(items, fp, ensure_ascii=False, indent=2)
        fp.write("\n")
    print(f"[json] 已写入 {out_path}（{len(items)} 项）")


def update_json_lists():
    today = date.today().strftime("%Y%m%d")
    for sub, prefix in (("SFX", "siren_sfx_list"), ("Ambience", "siren_ambience_list")):
        items = collect_audio(REPO / sub)
        write_json(items, REPO / f"{prefix}_{today}.json")
        # 提示旧的带日期列表文件
        for old in REPO.glob(f"{prefix}_*.json"):
            if old.name != f"{prefix}_{today}.json":
                print(f"[json] 注意：存在旧列表文件 {old.name}，确认无误后可手动删除")


def main():
    update_tree_txt()
    update_json_lists()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
