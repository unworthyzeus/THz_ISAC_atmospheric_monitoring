"""Repository-local provenance helper, packaged from the research portfolio."""
import hashlib
import json
import os
from pathlib import Path
import platform
import threading
import time
import psutil

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


class Run:
    def __init__(self, output, protocol, source):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.protocol = protocol
        self.source = Path(source)
        write_json(self.output / "protocol.json", protocol)
        self.start = time.perf_counter()
        self.peak = 0
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.sample, daemon=True)
        self.thread.start()

    def sample(self):
        process = psutil.Process()
        while not self.stop.is_set():
            self.peak = max(self.peak, process.memory_info().rss)
            self.stop.wait(.1)

    def finish(self, failures=(), extra=None):
        self.stop.set()
        self.thread.join()
        import importlib.metadata
        versions = {}
        for package in ("numpy", "scipy", "pandas", "torch", "scikit-learn", "sympy", "cvxpy"):
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                pass
        record = dict(protocol=self.protocol, wall_seconds=time.perf_counter()-self.start,
                      sampled_peak_rss_bytes=self.peak, memory_sampling_seconds=.1,
                      python=platform.python_version(), platform=platform.platform(),
                      cpu=platform.processor(), cpu_only=True, software=versions,
                      command=os.sys.argv, failures=list(failures),
                      code_sha256=digest(self.source),
                      outputs={p.name: digest(p) for p in self.output.iterdir()
                               if p.is_file() and p.name != "manifest.json"})
        if extra:
            record.update(extra)
        write_json(self.output / "manifest.json", record)


def paired_summary(frame, keys, method, reference, metric, seed=609052):
    import numpy as np
    rows=[]
    for values, group in frame.groupby(keys):
        if not isinstance(values, tuple):
            values=(values,)
        wide=group.pivot(index="seed", columns="method", values=metric)
        diff=(wide[method]-wide[reference]).to_numpy()
        boot=diff[np.random.default_rng(seed).integers(0,len(diff),(20000,len(diff)))].mean(1)
        rows.append(dict(zip(keys,values), method=method, reference=reference, metric=metric,
            n=len(diff), mean=float(wide[method].mean()), reference_mean=float(wide[reference].mean()),
            difference=float(diff.mean()), ci_low=float(np.quantile(boot,.025)),
            ci_high=float(np.quantile(boot,.975))))
    return rows
