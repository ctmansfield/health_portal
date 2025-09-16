#!/usr/bin/env python3
import sys, json, os, re

def n(s):
    import re
    return re.sub(r"\s+"," ",(s or "")).strip()

if len(sys.argv) < 3:
    print("Usage: gen_runtime.py <repo_root> <profile>")
    sys.exit(1)

root, profile = sys.argv[1], sys.argv[2]
cfg_path = os.path.join(root, "config", "backends.json")
if not os.path.exists(cfg_path):
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "backends.json")

with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

if profile not in cfg:
    print("Unknown profile:", profile)
    print("Available:", ", ".join(cfg.keys()))
    sys.exit(2)

meta = cfg[profile]
api = n(meta.get("api_base",""))
fhir = n(meta.get("fhir_base",""))
cds = n(meta.get("cds_hooks",""))
aud = n(meta.get("audience",""))
mock = bool(meta.get("mock", False))

# 1) .env.local
env_lines = []
env_lines.append(f"API_PROFILE={profile}")
env_lines.append(f"VITE_API_BASE={api}")
env_lines.append(f"VITE_FHIR_BASE={fhir}")
env_lines.append(f"VITE_CDS_HOOKS={cds}")
env_lines.append(f"NEXT_PUBLIC_API_BASE={api}")
env_lines.append(f"NEXT_PUBLIC_FHIR_BASE={fhir}")
env_lines.append(f"NEXT_PUBLIC_CDS_HOOKS={cds}")
env_lines.append(f"REACT_APP_API_BASE={api}")
env_lines.append(f"REACT_APP_FHIR_BASE={fhir}")
env_lines.append(f"REACT_APP_CDS_HOOKS={cds}")
if aud:
    env_lines.append(f"API_AUDIENCE={aud}")
env_lines.append(f"API_MOCK={'1' if mock else '0'}")

os.makedirs(root, exist_ok=True)
with open(os.path.join(root, ".env.local"), "w", encoding="utf-8") as f:
    f.write("\n".join(env_lines)+"\n")

# 2) src/config/runtime.generated.json
runtime = {
    "PROFILE": profile,
    "API_BASE": api,
    "FHIR_BASE": fhir,
    "CDS_HOOKS": cds,
    "AUDIENCE": aud,
    "MOCK": mock
}
dst_json = os.path.join(root, "src", "config")
os.makedirs(dst_json, exist_ok=True)
with open(os.path.join(dst_json, "runtime.generated.json"), "w", encoding="utf-8") as f:
    json.dump(runtime, f, indent=2)

# 3) public/runtime-config.json
pub_dir = os.path.join(root, "public")
os.makedirs(pub_dir, exist_ok=True)
with open(os.path.join(pub_dir, "runtime-config.json"), "w", encoding="utf-8") as f:
    json.dump(runtime, f, indent=2)

print("OK")
