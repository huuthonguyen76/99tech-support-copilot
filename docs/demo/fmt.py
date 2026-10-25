"""Pretty-print Claude Code stream-json: tool calls, short results, final text."""
import json, sys, textwrap
B, D, C, G, Y, R, M, X = "\033[1m", "\033[2m", "\033[36m", "\033[32m", "\033[33m", "\033[31m", "\033[35m", "\033[0m"
for line in sys.stdin:
    try: m = json.loads(line)
    except json.JSONDecodeError: continue
    if m.get("type") == "assistant":
        for b in m["message"].get("content", []):
            if b.get("type") == "tool_use":
                name = b["name"].split("__")[-1]
                args = {k: (v if len(str(v)) < 70 else str(v)[:67] + "...") for k, v in b["input"].items()}
                print(f"{C}{B}→ {name}{X}{C}({json.dumps(args, ensure_ascii=False)}){X}", flush=True)
    elif m.get("type") == "user":
        for b in m["message"].get("content", []):
            if not isinstance(b, dict) or b.get("type") != "tool_result": continue
            txt = b["content"][0]["text"] if isinstance(b["content"], list) else str(b["content"])
            try: r = json.loads(txt)
            except Exception: print(f"{D}  ← {txt[:120]}{X}"); continue
            if "assessment" in r:
                a = r["assessment"]
                print(f"{D}  ← {a['priority']} {a['category']} lang={a['reply_language']} escalate={a['escalate_to']}{X}")
                for f in a["findings"]:
                    col = R if f["severity"] in ("critical", "high") else D
                    print(f"{col}     • {f['code']}{X}")
            elif r.get("saved") is False:
                for v in r["violations"]: print(f"{R}{B}  ← BLOCKED by guardrail: {v['code']}{X}{R} {v['detail'][:90]}{X}")
            elif r.get("saved"):
                print(f"{G}  ← draft saved, status={r['status']} (not sent){X}")
            elif "recorded" in r:
                print((G if r["recorded"] else Y) + f"  ← recorded={r['recorded']} " + str(r.get("status") or r.get("team") or r.get("reason", ""))[:110] + X)
            else:
                print(f"{D}  ← {txt[:120]}{X}")
    elif m.get("type") == "result":
        print(f"\n{M}{B}Claude:{X}")
        for para in m.get("result", "").splitlines():
            print(textwrap.fill(para, 116) if para.strip() else "")
