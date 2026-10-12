"""Kaggle driver for the PRISM VLM pipeline (GPU stages). Resumable across sessions:
everything worth keeping lives in /kaggle/working/state; attach a previous run's state as a dataset
(any file named STATE_MARKER inside it) and this run continues from there."""

import glob
import os
import shutil
import signal
import subprocess
import sys
import time

MODE = "full"           # "smoke" = env check + smoke test only; "full" = whole pipeline
BUDGET_H = 11.2        # stop children cleanly before Kaggle's 12 h limit
T0 = time.time()
W = "/kaggle/working/state"
PROJ = "/tmp/prism_vlm"
os.makedirs(os.path.join(W, "logs"), exist_ok=True)
open(os.path.join(W, "STATE_MARKER"), "w").write("prism state\n")


def log(msg):
    line = f"[driver {(time.time() - T0) / 60:6.1f} min] {msg}"
    print(line, flush=True)
    with open(os.path.join(W, "driver_log.txt"), "a") as f:
        f.write(line + "\n")


def left():
    return BUDGET_H * 3600 - (time.time() - T0)


def find(pattern):
    hits = glob.glob(f"/kaggle/input/**/{pattern}", recursive=True)
    return hits[0] if hits else None


def start(name, args, gpu=None):
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    if gpu is not None:
        env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    fh = open(os.path.join(W, "logs", f"{name}.log"), "a")
    log(f"start {name} (gpu={gpu}): {' '.join(args)}")
    p = subprocess.Popen([sys.executable] + args, cwd=PROJ, env=env, stdout=fh, stderr=subprocess.STDOUT)
    p._name, p._fh = name, fh
    return p


def wait(procs):
    """Wait for all; on budget exhaustion send SIGINT then kill. Returns {name: returncode}."""
    rc = {}
    while procs:
        for p in list(procs):
            if p.poll() is not None:
                p._fh.close()
                rc[p._name] = p.returncode
                log(f"end {p._name}: exit {p.returncode}")
                tail(p._name)
                procs.remove(p)
        if procs and left() < 0:
            log("time budget reached - stopping running stages (they resume next session)")
            for p in procs:
                p.send_signal(signal.SIGINT)
            time.sleep(120)
            for p in procs:
                if p.poll() is None:
                    p.kill()
            for p in procs:
                p.wait()
                rc[p._name] = "stopped"
            touch("OUT_OF_TIME")
            break
        time.sleep(20)
    return rc


def tail(name, n=40):
    path = os.path.join(W, "logs", f"{name}.log")
    lines = open(path, errors="replace").read().splitlines()
    print("\n".join(f"    | {l}" for l in lines[-n:]), flush=True)


def done(stage):
    return os.path.exists(os.path.join(W, f"DONE_{stage}"))


def touch(stage):
    open(os.path.join(W, f"DONE_{stage}" if not stage.isupper() else stage), "w").write(time.ctime())


def run(name, args, gpu=None):
    rc = wait([start(name, args, gpu)])
    return rc.get(name) == 0


# ---------------------------------------------------------------- setup
cfg_path = find("configs/config.yaml")
pairs = find("pairs/train.jsonl")
prev = [p for p in glob.glob("/kaggle/input/**/STATE_MARKER", recursive=True)]
log(f"code: {cfg_path}\ndata pairs: {pairs}\nprevious state: {prev}")
code_root = os.path.dirname(os.path.dirname(cfg_path))
data_root = os.path.dirname(os.path.dirname(pairs))
if prev:
    src = os.path.dirname(prev[0])
    for item in os.listdir(src):
        s, d = os.path.join(src, item), os.path.join(W, item)
        if item in ("STATE_MARKER", "OUT_OF_TIME") or os.path.exists(d):
            continue
        (shutil.copytree if os.path.isdir(s) else shutil.copy2)(s, d)
    log(f"restored state from {src}: {sorted(os.listdir(W))}")

shutil.rmtree(PROJ, ignore_errors=True)
os.makedirs(PROJ)
for sub in ("prism", "scripts", "configs"):
    shutil.copytree(os.path.join(code_root, sub), os.path.join(PROJ, sub))
os.symlink(data_root, os.path.join(PROJ, "data"))
for sub in ("outputs", "predictions", "reports"):
    os.makedirs(os.path.join(W, sub), exist_ok=True)
    os.symlink(os.path.join(W, sub), os.path.join(PROJ, sub))

subprocess.run("nvidia-smi --query-gpu=name,memory.total --format=csv", shell=True)
log("installing pinned libraries")
r = subprocess.run(f"{sys.executable} -m pip install -q transformers==4.51.3 trl==0.17.0 peft==0.15.2 "
                   "'accelerate>=1.6.0' 'bitsandbytes>=0.45.0' 'datasets>=3.0' qwen-vl-utils==0.0.11",
                   shell=True, capture_output=True, text=True)
print(r.stdout[-3000:], r.stderr[-3000:], flush=True)
subprocess.run(f"{sys.executable} -c \"import torch,transformers,trl,peft,bitsandbytes;"
               "print('torch',torch.__version__,'cuda',torch.version.cuda,'transformers',transformers.__version__,"
               "'trl',trl.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__)\""
               f" | tee -a {W}/driver_log.txt", shell=True)

import torch  # noqa: E402
import yaml  # noqa: E402

n_gpu = torch.cuda.device_count()
mem = torch.cuda.get_device_properties(0).total_memory / 2**30 if n_gpu else 0
log(f"{n_gpu} GPU(s), {mem:.1f} GB each")
cfg_file = os.path.join(PROJ, "configs", "config.yaml")
cfg = yaml.safe_load(open(cfg_file))
if mem < 20:  # low-VRAM settings (see README): 2 epochs, prompt_study_n 30, max_pixels 501760, batch 2
    cfg["model"]["max_pixels"] = 501760
    cfg["inference"]["batch_size"] = 2
    cfg["train"]["epochs"] = 2
    cfg["inference"]["prompt_study_n"] = 30
    log("config for <20 GB GPU: max_pixels 501760, inference.batch_size 2, train.epochs 2, prompt_study_n 30")
yaml.safe_dump(cfg, open(cfg_file, "w"), sort_keys=False)
shutil.copy(cfg_file, os.path.join(W, "config_used.yaml"))

# ---------------------------------------------------------------- stages
if not done("smoke"):
    if not run("smoke", ["scripts/gpu_smoke_test.py"], gpu=0):
        log("SMOKE TEST FAILED - see logs/smoke.log"); sys.exit(1)
    if "SMOKE TEST PASSED" in open(os.path.join(W, "logs", "smoke.log")).read():
        touch("smoke")
if MODE == "smoke":
    log("smoke mode finished"); sys.exit(0)

jobs = []
if not done("train"):
    jobs.append(("train", ["scripts/04_train_qlora.py"]))
if not done("baseline"):
    jobs.append(("baseline", ["scripts/03_prompt_study_and_baseline.py"]))
if n_gpu > 1:  # two T4s: baseline and training in parallel, one GPU each
    rc = wait([start(name, args, gpu=i) for i, (name, args) in enumerate(jobs)])
else:
    rc = {}
    for name, args in jobs:
        if not os.path.exists(os.path.join(W, "OUT_OF_TIME")):
            rc.update(wait([start(name, args, gpu=0)]))
for k, v in rc.items():
    if v == 0:
        touch(k)
if os.path.exists(os.path.join(W, "OUT_OF_TIME")) or not (done("train") and done("baseline")):
    log(f"stopping: train={done('train')} baseline={done('baseline')} - rerun with this output attached"); sys.exit(0)

if not done("infer"):
    if run("infer", ["scripts/05_infer.py", "--adapter", "outputs/best_adapter", "--name", "finetuned_qlora",
                     "--split", "test"], gpu=0):
        touch("infer")
    else:
        log("inference did not finish"); sys.exit(0)

if run("evaluate", ["scripts/06_evaluate.py", "--models", "baseline_zero_shot", "finetuned_qlora", "--split", "test"]):
    touch("evaluate")
# drop optimizer-heavy checkpoints from the final output once everything is done
shutil.rmtree(os.path.join(W, "outputs", "checkpoints"), ignore_errors=True)
log("PIPELINE COMPLETE")
