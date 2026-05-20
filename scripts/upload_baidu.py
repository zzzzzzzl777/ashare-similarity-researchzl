"""Upload files to Baidu Netdisk via REST API (bypasses bypy slice MD5 bug)."""
import json, os, hashlib, requests, math, time, sys
from pathlib import Path

with open(os.path.expanduser("~/.bypy/bypy.json")) as f:
    ACCESS_TOKEN = json.load(f)["access_token"]

REMOTE_DIR = "/apps/bypy/1457_live_deploy"
SLICE_SIZE = 4 * 1024 * 1024  # 4MB per slice

FILES = [
    Path("D:/1457_live_extra.7z"),
    Path("D:/1457_live_code.7z"),
    Path("D:/1457_live_data.7z.001"),
    Path("D:/1457_live_data.7z.002"),
    Path("D:/1457_live_data.7z.003"),
]


def slice_md5s(path: Path) -> list[str]:
    md5s = []
    with open(path, "rb") as f:
        while True:
            chunk = f.read(SLICE_SIZE)
            if not chunk:
                break
            md5s.append(hashlib.md5(chunk).hexdigest())
    return md5s


def precreate(remote_path: str, file_size: int, block_list: list[str]):
    r = requests.post(
        "https://pan.baidu.com/rest/2.0/xpan/file",
        params={"method": "precreate", "access_token": ACCESS_TOKEN},
        data={
            "path": remote_path,
            "size": file_size,
            "isdir": 0,
            "autoinit": 1,
            "rtype": 3,
            "block_list": json.dumps(block_list),
        },
    )
    return r.json()


def upload_slice(upload_id: str, remote_path: str, part_seq: int, data: bytes):
    for attempt in range(5):
        try:
            r = requests.post(
                "https://d.pcs.baidu.com/rest/2.0/pcs/superfile2",
                params={
                    "method": "upload",
                    "access_token": ACCESS_TOKEN,
                    "type": "tmpfile",
                    "path": remote_path,
                    "uploadid": upload_id,
                    "partseq": part_seq,
                },
                files={"file": ("chunk", data)},
                timeout=120,
            )
            resp = r.json()
            if "md5" in resp:
                return resp
            print(f"    Slice {part_seq} unexpected response: {resp}, retry {attempt+1}")
        except Exception as e:
            print(f"    Slice {part_seq} error: {e}, retry {attempt+1}")
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Failed to upload slice {part_seq} after 5 attempts")


def create_file(remote_path: str, file_size: int, upload_id: str, block_list: list[str]):
    r = requests.post(
        "https://pan.baidu.com/rest/2.0/xpan/file",
        params={"method": "create", "access_token": ACCESS_TOKEN},
        data={
            "path": remote_path,
            "size": file_size,
            "isdir": 0,
            "rtype": 3,
            "uploadid": upload_id,
            "block_list": json.dumps(block_list),
        },
    )
    return r.json()


def upload_file(local_path: Path):
    file_size = local_path.stat().st_size
    remote_path = f"{REMOTE_DIR}/{local_path.name}"
    size_mb = file_size / 1024 / 1024
    print(f"\n[Upload] {local_path.name} ({size_mb:.1f} MB) -> {remote_path}")

    print("  Computing slice MD5s...")
    block_list = slice_md5s(local_path)
    print(f"  {len(block_list)} slices")

    print("  Precreating...")
    pre = precreate(remote_path, file_size, block_list)
    if pre.get("errno", -1) != 0:
        print(f"  Precreate error: {pre}")
        return False
    upload_id = pre["uploadid"]
    if pre.get("return_type") == 2:
        print("  Rapid upload! (file already on server)")
        return True

    uploaded_md5s = []
    with open(local_path, "rb") as f:
        for i in range(len(block_list)):
            data = f.read(SLICE_SIZE)
            t0 = time.time()
            resp = upload_slice(upload_id, remote_path, i, data)
            elapsed = time.time() - t0
            speed = len(data) / elapsed / 1024 / 1024 if elapsed > 0 else 0
            uploaded_md5s.append(resp["md5"])
            pct = (i + 1) / len(block_list) * 100
            print(f"  [{pct:5.1f}%] Slice {i+1}/{len(block_list)} OK ({speed:.1f} MB/s)")

    print("  Merging...")
    result = create_file(remote_path, file_size, upload_id, uploaded_md5s)
    if result.get("errno", -1) != 0:
        print(f"  Create error: {result}")
        return False
    print(f"  Done! fs_id={result.get('fs_id')}")
    return True


if __name__ == "__main__":
    t_start = time.time()
    results = {}
    for fp in FILES:
        if not fp.exists():
            print(f"SKIP {fp} (not found)")
            results[fp.name] = "skipped"
            continue
        ok = upload_file(fp)
        results[fp.name] = "OK" if ok else "FAILED"

    print("\n" + "=" * 50)
    print("Upload Summary:")
    for name, status in results.items():
        print(f"  {name}: {status}")
    print(f"Total time: {time.time() - t_start:.0f}s")
