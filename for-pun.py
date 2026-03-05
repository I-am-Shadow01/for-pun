import requests
import time
import random
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# =========================
# CONFIG
# =========================

SUPABASE_URL = "https://magnudsyqmyqrxhqbcyx.supabase.co/rest/v1/messages"

apikey = "" #ไปดักเองดิ
jwt_token = "" #ไปดักเองดิ
user_id = "" #ไปดักเองดิ

# =========================
# STRESS SETTINGS
# =========================

TOTAL_MESSAGES = 2000       # จำนวน message ทั้งหมด
MAX_WORKERS    = 40        # จำนวน thread พร้อมกัน (concurrent)
DELAY_BETWEEN  = 0.03      # delay ต่อ thread (วินาที) — 0 = เร็วสุด

# =========================
# CONTENT POOL
# =========================

EMOJIS = [
    "🔥","🚀","💥","✨","😂","🤣","😎","🤖","👾","⚡",
    "🌊","🌌","🎯","🧠","💡","🛰️","🌀","🌍","🧬","🎮",
    "🐉","🦄","🍕","🎸","🏆","🎲","🌈","⚔️","🛸","🧨",
    "🦋","🐋","🦖","🍔","🎭","🏄","🌺","🍄","🎪","🔮",
    "🧊","🌋","🦅","🐺","🌙","☄️","🎆","🎇","🏔️","🦁",
    "🐲","🍀","⭐","🌟","💫","🎠","🎡","🎢","🎯","🎳",
    "🦊","🐯","🦝","🦩","🦚","🦜","🐬","🦈","🐙","🦑"
]

WORDS = [
    "hello","python","bot","test","spam","realtime",
    "supabase","message","system","ping","pong",
    "stress","flood","concurrent","thread","async"
]

SENTENCES = [
    "testing realtime latency",
    "concurrent insert benchmark",
    "stress test in progress",
    "สวัสดี database !!",
    "how fast can supabase go",
    "insert insert insert",
]

def random_content():
    # สุ่ม 50 emoji (with replacement เพราะ pool มี 70 ตัว)
    emoji_block = "".join(random.choices(EMOJIS, k=50))
    mode = random.randint(0, 2)
    if mode == 0:
        return f"{random.choice(WORDS)} {emoji_block}"
    elif mode == 1:
        return f"{random.choice(SENTENCES)} {emoji_block}"
    else:
        words = random.sample(WORDS, 3)
        return f"{' '.join(words)} {emoji_block}"

# =========================
# HEADERS
# =========================

headers = {
    "apikey": apikey,
    "Authorization": f"Bearer {jwt_token}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# =========================
# STATS (thread-safe)
# =========================

lock = threading.Lock()
stats = {
    "success": 0,
    "fail": 0,
    "total_ms": 0.0,
    "min_ms": float("inf"),
    "max_ms": 0.0,
    "errors": []
}

# =========================
# SEND FUNCTION
# =========================

def send_message(index: int):
    content = random_content()
    payload = {
        "user_id": user_id,
        "content": f"[#{index:03d}] {content}",
        "reply_to": None
    }

    start = time.perf_counter()
    try:
        r = requests.post(SUPABASE_URL, headers=headers, json=payload, timeout=10)
        elapsed_ms = (time.perf_counter() - start) * 1000

        ok = r.status_code in (200, 201)

        with lock:
            if ok:
                stats["success"] += 1
            else:
                stats["fail"] += 1
                stats["errors"].append(f"[#{index:03d}] HTTP {r.status_code}: {r.text[:80]}")
            stats["total_ms"] += elapsed_ms
            stats["min_ms"] = min(stats["min_ms"], elapsed_ms)
            stats["max_ms"] = max(stats["max_ms"], elapsed_ms)

        status_icon = "✅" if ok else "❌"
        print(f"{status_icon} #{index:03d} | {r.status_code} | {elapsed_ms:.0f}ms | {content[:40]}")

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        with lock:
            stats["fail"] += 1
            stats["errors"].append(f"[#{index:03d}] EXCEPTION: {e}")
        print(f"💀 #{index:03d} | EXCEPTION | {elapsed_ms:.0f}ms | {e}")

    time.sleep(DELAY_BETWEEN)

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    print("=" * 60)
    print(f"🚀 STRESS TEST START")
    print(f"   Messages  : {TOTAL_MESSAGES}")
    print(f"   Workers   : {MAX_WORKERS} concurrent threads")
    print(f"   Delay/req : {DELAY_BETWEEN}s")
    print(f"   Target    : {SUPABASE_URL}")
    print("=" * 60)

    overall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(send_message, i + 1) for i in range(TOTAL_MESSAGES)]
        for f in as_completed(futures):
            pass  # ผลแต่ละ request print ใน send_message แล้ว

    overall_elapsed = time.perf_counter() - overall_start
    total_done = stats["success"] + stats["fail"]
    avg_ms = stats["total_ms"] / total_done if total_done > 0 else 0
    rps = TOTAL_MESSAGES / overall_elapsed

    print()
    print("=" * 60)
    print(f"📊 RESULTS")
    print(f"   Total sent    : {TOTAL_MESSAGES}")
    print(f"   ✅ Success    : {stats['success']}")
    print(f"   ❌ Failed     : {stats['fail']}")
    print(f"   ⏱  Total time : {overall_elapsed:.2f}s")
    print(f"   ⚡ Req/sec    : {rps:.1f} rps")
    print(f"   📈 Avg latency: {avg_ms:.0f}ms")
    print(f"   🔼 Max latency: {stats['max_ms']:.0f}ms")
    print(f"   🔽 Min latency: {stats['min_ms']:.0f}ms")

    if stats["errors"]:
        print()
        print(f"   ⚠️  ERRORS ({len(stats['errors'])}):")
        for e in stats["errors"][:10]:  # แสดงแค่ 10 แรก
            print(f"      {e}")

    print("=" * 60)

    print(f"✅ DONE at {datetime.now().strftime('%H:%M:%S')}")
