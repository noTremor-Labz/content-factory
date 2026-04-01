#!/usr/bin/env python3
"""
pixel_upload.py — генерация медиа и загрузка в Cloudflare R2
Универсальный скрипт для всех блогеров и площадок.

Использование:
  python3 pixel_upload.py \
    --job_id 20250612-001 \
    --blogger tomas \
    --platform tg \
    --prompt_file /path/to/image_prompt.txt

Площадки (--platform):
  tg       → статичное изображение 1:1    (fal.ai flux-dev → fallback Replicate)
  reels    → видео 9:16                   (Kling → fallback RunwayML)
  shorts   → видео 9:16                   (Kling → fallback RunwayML)
  tt       → видео 9:16                   (Kling → fallback RunwayML)

Переменные окружения (.env / docker-compose):
  R2_ACCOUNT_ID          Cloudflare Account ID
  R2_ACCESS_KEY_ID       R2 Access Key
  R2_SECRET_ACCESS_KEY   R2 Secret Key
  R2_BUCKET_RAW          бакет (default: media-raw)
  R2_PUBLIC_URL          https://... публичный URL бакета
  FAL_API_KEY            fal.ai (фото, primary)
  REPLICATE_API_TOKEN    Replicate (фото, fallback)
  KLING_API_KEY          Kling (видео, primary)
  RUNWAYML_API_SECRET    RunwayML (видео, fallback)
"""

import argparse, os, sys, uuid, datetime, time, re, json
import urllib.request
import boto3
from botocore.config import Config
from pathlib import Path

VIDEO_PLATFORMS = {"reels", "shorts", "tt"}


def env(key, default=None):
    v = os.environ.get(key, default)
    if v is None:
        print(f"ERROR: {key} не задан", file=sys.stderr)
        sys.exit(1)
    return v


def parse_prompt(text):
    positive_lines, negative = [], ""
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^Negative:", s, re.I):
            negative = re.sub(r"^Negative:\s*", "", s, flags=re.I)
        elif re.match(r"^(Platform|Blogger|Job|--|--ar|--style)", s, re.I):
            continue
        elif s:
            positive_lines.append(s)
    return " ".join(positive_lines), negative or "watermark, text overlay, cartoon, illustration"


# ── фото ─────────────────────────────────────────────────────────────────────

def _download(url):
    with urllib.request.urlopen(url) as r:
        return r.read()

def gen_photo_fal(pos, neg):
    import fal_client
    
    result = fal_client.run("fal-ai/flux/dev", arguments={
        "prompt": pos, "negative_prompt": neg,
        "image_size": "square_hd", "num_inference_steps": 28,
        "guidance_scale": 3.5, "num_images": 1, "enable_safety_checker": False,
    })
    return _download(result["images"][0]["url"])

def gen_photo_replicate(pos, neg):
    import replicate
    out = replicate.Client(api_token=env("REPLICATE_API_TOKEN")).run(
        "black-forest-labs/flux-dev",
        input={"prompt": pos, "negative_prompt": neg, "aspect_ratio": "1:1",
               "output_format": "jpeg", "output_quality": 90,
               "num_inference_steps": 28, "guidance": 3.5}
    )
    return _download(str(out[0]) if isinstance(out, list) else str(out))

def generate_photo(pos, neg):
    if os.environ.get("FAL_API_KEY"):
        print("[Pixel] fal.ai flux-dev...", flush=True)
        try:
            return gen_photo_fal(pos, neg), "jpg"
        except Exception as e:
            print(f"[Pixel] fal.ai fail: {e} → Replicate", file=sys.stderr)
    if os.environ.get("REPLICATE_API_TOKEN"):
        print("[Pixel] Replicate flux-dev...", flush=True)
        return gen_photo_replicate(pos, neg), "jpg"
    raise RuntimeError("Нет FAL_API_KEY и REPLICATE_API_TOKEN")


# ── видео ─────────────────────────────────────────────────────────────────────

def _poll(url, headers, status_field, success_val, fail_val, get_url_fn, timeout=60):
    for _ in range(timeout):
        time.sleep(5)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        st = status_field(data)
        if st == success_val:
            return _download(get_url_fn(data))
        if st == fail_val:
            raise RuntimeError(f"failed: {data}")
    raise RuntimeError("timeout (5 мин)")

def gen_video_kling(pos):
    key = env("KLING_API_KEY")
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    req = urllib.request.Request(
        "https://api.klingai.com/v1/videos/text2video",
        data=json.dumps({"model": "kling-v1", "prompt": pos,
                         "aspect_ratio": "9:16", "duration": 5, "mode": "std"}).encode(),
        headers=h, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        task_id = json.loads(r.read())["data"]["task_id"]
    print(f"[Pixel] Kling task={task_id}", flush=True)
    poll_url = f"https://api.klingai.com/v1/videos/text2video/{task_id}"
    return _poll(poll_url, {"Authorization": f"Bearer {key}"},
                 lambda d: d["data"]["task_status"], "succeed", "failed",
                 lambda d: d["data"]["task_result"]["videos"][0]["url"])

def gen_video_runway(pos):
    secret = env("RUNWAYML_API_SECRET")
    v = "2024-11-06"
    h = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json", "X-Runway-Version": v}
    req = urllib.request.Request(
        "https://api.dev.runwayml.com/v1/image_to_video",
        data=json.dumps({"model": "gen3a_turbo", "promptText": pos,
                         "ratio": "768:1280", "duration": 5}).encode(),
        headers=h, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        task_id = json.loads(r.read())["id"]
    print(f"[Pixel] RunwayML task={task_id}", flush=True)
    return _poll(f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
                 {"Authorization": f"Bearer {secret}", "X-Runway-Version": v},
                 lambda d: d.get("status"), "SUCCEEDED", "FAILED",
                 lambda d: d["output"][0])

def generate_video(pos):
    if os.environ.get("KLING_API_KEY"):
        print("[Pixel] Kling v1...", flush=True)
        try:
            return gen_video_kling(pos), "mp4"
        except Exception as e:
            print(f"[Pixel] Kling fail: {e} → RunwayML", file=sys.stderr)
    if os.environ.get("RUNWAYML_API_SECRET"):
        print("[Pixel] RunwayML Gen-3 Turbo...", flush=True)
        return gen_video_runway(pos), "mp4"
    raise RuntimeError("Нет KLING_API_KEY и RUNWAYML_API_SECRET")


# ── R2 ────────────────────────────────────────────────────────────────────────

def upload_to_r2(data, blogger, job_id, platform, ext):
    s3 = boto3.client("s3",
        endpoint_url=f"https://{env('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=env("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    key = (f"{blogger}/{datetime.date.today().isoformat()}/{job_id}/"
           f"{'video' if ext=='mp4' else 'image'}_{uuid.uuid4().hex[:8]}.{ext}")
    s3.put_object(
        Bucket=env("R2_BUCKET_RAW", "media-raw"),
        Key=key,
        Body=data,
        ContentType="video/mp4" if ext == "mp4" else "image/jpeg",
        Metadata={"blogger": blogger, "job_id": job_id, "platform": platform},
    )
    return f"{env('R2_PUBLIC_URL').rstrip('/')}/{key}"


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--job_id",      required=True)
    p.add_argument("--blogger",     required=True)
    p.add_argument("--platform",    required=True, choices=["tg", "reels", "shorts", "tt"])
    p.add_argument("--prompt_file", required=True)
    args = p.parse_args()

    path = Path(args.prompt_file)
    if not path.exists():
        print(f"ERROR: промпт не найден: {path}", file=sys.stderr); sys.exit(1)

    pos, neg = parse_prompt(path.read_text(encoding="utf-8"))
    if not pos:
        print("ERROR: промпт пустой", file=sys.stderr); sys.exit(1)

    print(f"[Pixel] {args.blogger}/{args.platform}/{args.job_id}")
    print(f"[Pixel] prompt: {pos[:100]}...", flush=True)

    t0 = time.time()
    try:
        data, ext = generate_video(pos) if args.platform in VIDEO_PLATFORMS else generate_photo(pos, neg)
    except Exception as e:
        print(f"ERROR: генерация: {e}", file=sys.stderr); sys.exit(1)

    print(f"[Pixel] {time.time()-t0:.1f}с, {len(data)//1024}кб → R2...", flush=True)
    try:
        url = upload_to_r2(data, args.blogger, args.job_id, args.platform, ext)
    except Exception as e:
        print(f"ERROR: R2: {e}", file=sys.stderr); sys.exit(1)

    print(f"PIXEL_URL: {url}")


if __name__ == "__main__":
    main()
