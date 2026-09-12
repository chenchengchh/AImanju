# -*- coding: utf-8 -*-
"""临时审计：核对工作流模板节点/模型与 ComfyUI 实际可用项。用完可删。"""
import json
import re
import urllib.request

o = json.load(urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=60))
keys = set(o.keys())

nodes = [
    "MiniMaxH3TurboLoRA",
    "MiniMaxH3MemoryEfficientSageAttentionPatch",
    "MiniMaxH3GenerationTailLoader",
    "MiniMaxH3PromptEnhancer",
    "MiniMaxH3TextEncoder",
    "MiniMaxH3ImageToVideo",
    "MiniMaxH3ReferenceToVideo",
]
print("== 自定义节点 ==")
for n in nodes:
    print(f"  {n}: {'OK' if n in keys else 'MISSING'}")

print("== 工作流模板 class_type 对比 ==")
for f in ["workflows/r2v_api_template.json", "workflows/i2v_api_template.json"]:
    t = open(f, encoding="utf-8").read()
    cts = set(re.findall(r'"class_type"\s*:\s*"([\w\.]+)"', t))
    miss = sorted(cts - keys)
    print(f"  {f}: missing={miss if miss else '(none)'}")

print("== 工作流模板引用的模型文件 vs ComfyUI 可用列表 ==")
def obj_list(cls, key):
    try:
        return set(o[cls]["input"]["required"][key][0])
    except Exception:
        return set()

avail = {
    "unet": obj_list("UNETLoader", "unet_name"),
    "clip": obj_list("CLIPLoader", "clip_name"),
    "vae": obj_list("VAELoader", "vae_name"),
    "lora": obj_list("LoraLoader", "lora_name"),
    "tail": obj_list("MiniMaxH3GenerationTailLoader", "model_name")
    or obj_list("MiniMaxH3GenerationTailLoader", "tail_name"),
}
print("  tail_loader 可选列表:", sorted(avail["tail"]) or "(节点缺失)")
for f in ["workflows/r2v_api_template.json", "workflows/i2v_api_template.json"]:
    t = open(f, encoding="utf-8").read()
    models = sorted(set(re.findall(r"[\w\.]+\.safetensors", t)))
    for m in models:
        hit = any(m in v for v in avail.values())
        print(f"  {f} :: {m}: {'OK' if hit else 'MISSING'}")
