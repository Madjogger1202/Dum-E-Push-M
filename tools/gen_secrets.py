# tools/gen_secrets.py
import os, json, re
from pathlib import Path

OUT = Path("include/generated_secrets.h")
SRC_JSON = Path(".secrets.json")

def get_env(name):
    v = os.getenv(name)
    return v.strip() if v else None

# 1) читаем из окружения
ssid  = get_env("WIFI_SSID")
pwd   = get_env("WIFI_PASS")
token = get_env("BOT_TOKEN")
ids_s = get_env("ALLOWED_IDS")  # строка: "111, -222"

# 2) при наличии .secrets.json — дополняем/перекрываем
if SRC_JSON.exists():
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    ssid  = ssid  or data.get("wifi_ssid")
    pwd   = pwd   or data.get("wifi_pass")
    token = token or data.get("bot_token")
    if not ids_s:
        ids = data.get("allowed_ids")
        if isinstance(ids, list):
            ids_s = ",".join(str(x) for x in ids)

# 3) парсим ID
ids_list = []
if ids_s:
    for x in re.split(r"[,\s]+", ids_s.strip()):
        if x:
            try:
                ids_list.append(int(x))
            except ValueError:
                pass

# 4) валидация
missing = [k for k, v in {
    "WIFI_SSID": ssid,
    "WIFI_PASS": pwd,
    "BOT_TOKEN": token,
    "ALLOWED_IDS": (ids_list if ids_list else None)
}.items() if not v]

OUT.parent.mkdir(parents=True, exist_ok=True)
if missing:
    OUT.write_text("// generated\n#error Missing secrets: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit(f"Missing secrets: {', '.join(missing)}")

# 5) строки в C
def cstr(s: str) -> str:
    return '"' + s.replace('\\','\\\\').replace('"','\\"') + '"'

# 6) формируем дефайны
defs = []
defs.append("// Auto-generated. DO NOT COMMIT.")
defs.append("#pragma once")
defs.append(f"#define WIFI_SSID {cstr(ssid)}")
defs.append(f"#define WIFI_PASS {cstr(pwd)}")
defs.append(f"#define BOT_TOKEN {cstr(token)}")

defs.append(f"#define ALLOWED_USERS_COUNT {len(ids_list)}")

# поэлементные ALLOWED_ID_n и список
elem_macros = []
for i, v in enumerate(ids_list):
    # 64-битный литерал; поддержка отрицательных значений
    lit = f"{v}LL" if v >= 0 else f"({v}LL)"
    defs.append(f"#define ALLOWED_ID_{i} {lit}")
    elem_macros.append(f"ALLOWED_ID_{i}")

if not elem_macros:
    defs.append("#error At least one allowed user id is required")
else:
    defs.append(f"#define CHAT_ID {elem_macros[0]}")  # первый = основной
    defs.append(f"#define ALLOWED_USERS_LIST " + ", ".join(elem_macros))

# Для удобства — сразу готовый массив (можно не использовать)
defs.append("")
defs.append("static const long long ALLOWED_IDS[ALLOWED_USERS_COUNT] = { ALLOWED_USERS_LIST };")

content = "\n".join(defs) + "\n"
OUT.write_text(content, encoding="utf-8")
print(f"[gen_secrets] Wrote {OUT}")
