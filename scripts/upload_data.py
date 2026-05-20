"""Upload remaining data files to Baidu Netdisk."""
import json, os, hashlib, requests, time
from pathlib import Path

with open(os.path.expanduser("~/.bypy/bypy.json")) as f:
    ACCESS_TOKEN = json.load(f)["access_token"]

REMOTE_DIR = "/apps/bypy/1457_live_deploy"
SLICE_SIZE = 4 * 1024 * 1024

FILES = [
    Path("D:/1457_live_data.7z.001"),
    Path("D:/1457_live_data.7z.002"),
    Path("D:/1457_live_data.7z.003"),
]

def upload_file(fp):
    file_size = fp.stat().st_size
    remote_path = f"{REMOTE_DIR}/{fp.name}"
    print(f"\n[Upload] {fp.name} ({file_size/1024/1024:.1f} MB)", flush=True)

    block_list = []
    with open(fp, "rb") as f:
        while True:
            chunk = f.read(SLICE_SIZE)
            if not chunk: break
            block_list.append(hashlib.md5(chunk).hexdigest())
    print(f"  {len(block_list)} slices, precreating...", flush=True)

    r = requests.post("https://pan.baidu.com/rest/2.0/xpan/file",
        params={"method": "precreate", "access_token": ACCESS_TOKEN},
        data={"path": remote_path, "size": file_size, "isdir": 0, "autoinit": 1, "rtype": 3,
              "block_list": json.dumps(block_list)})
    pre = r.json()
    if pre.get("return_type") == 2:
        print("  Rapid upload!", flush=True)
        return True
    if pre.get("errno", -1) != 0:
        print(f"  Precreate error: {pre}", flush=True)
        return False

    upload_id = pre["uploadid"]
    uploaded_md5s = []
    t0 = time.time()
    with open(fp, "rb") as f:
        for i in range(len(block_list)):
            data = f.read(SLICE_SIZE)
            for attempt in range(5):
                try:
                    r2 = requests.post("https://d.pcs.baidu.com/rest/2.0/pcs/superfile2",
                        params={"method": "upload", "access_token": ACCESS_TOKEN, "type": "tmpfile",
                                "path": remote_path, "uploadid": upload_id, "partseq": i},
                        files={"file": ("chunk", data)}, timeout=120)
                    resp = r2.json()
                    if "md5" in resp:
                        uploaded_md5s.append(resp["md5"])
                        break
                except Exception as e:
                    print(f"    Retry {attempt+1}: {e}", flush=True)
                    time.sleep(3)
            else:
                print(f"  FAILED at slice {i}", flush=True)
                return False
            if (i+1) % 100 == 0 or i+1 == len(block_list):
                elapsed = time.time() - t0
                speed = (i+1) * SLICE_SIZE / elapsed / 1024 / 1024
                pct = (i+1) / len(block_list) * 100
                print(f"  [{pct:5.1f}%] {i+1}/{len(block_list)} slices ({speed:.1f} MB/s)", flush=True)

    r3 = requests.post("https://pan.baidu.com/rest/2.0/xpan/file",
        params={"method": "create", "access_token": ACCESS_TOKEN},
        data={"path": remote_path, "size": file_size, "isdir": 0, "rtype": 3,
              "uploadid": upload_id, "block_list": json.dumps(uploaded_md5s)})
    result = r3.json()
    if result.get("errno", -1) == 0:
        print(f"  Done! fs_id={result['fs_id']}", flush=True)
        return True
    print(f"  Create error: {result}", flush=True)
    return False

if __name__ == "__main__":
    t_start = time.time()
    for fp in FILES:
        upload_file(fp)
    print(f"\nAll done in {time.time() - t_start:.0f}s", flush=True)
