"""CPU kernel: regenerate the PRISM dataset (seeded, identical to the local run) into /kaggle/working/data."""
import glob, os, shutil, subprocess, sys
cfg = glob.glob("/kaggle/input/**/configs/config.yaml", recursive=True)[0]
code = os.path.dirname(os.path.dirname(cfg))
proj = "/tmp/prism_vlm"
shutil.rmtree(proj, ignore_errors=True)
os.makedirs(proj)
for sub in ("prism", "scripts", "configs", "assets"):
    shutil.copytree(os.path.join(code, sub), os.path.join(proj, sub))
os.makedirs("/kaggle/working/data", exist_ok=True)
os.symlink("/kaggle/working/data", os.path.join(proj, "data"))
print("cpus", os.cpu_count(), flush=True)
for s in ("01_generate_dataset.py", "02_build_splits.py"):
    subprocess.run([sys.executable, f"scripts/{s}"], cwd=proj, check=True)
print("DATAGEN DONE", flush=True)
