import os
import sys
import time
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, r"c:\Users\Liang\minimax\RelateAnything")
from relsgg import RelateAnything

ckpt_path = r"c:\Users\Liang\minimax\RelateAnything\checkpoints\relsgg-vits16plus\model.pth"
img_dir = r"c:\Users\Liang\minimax\RelateAnything\assets\reel\images"

print("=" * 70)
print("1. ENVIRONMENT & HARDWARE INFO")
print("=" * 70)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"PyTorch Version : {torch.__version__}")
print(f"Device          : {torch.cuda.get_device_name(0) if device == 'cuda' else 'CPU'}")

if device == "cuda":
    torch.cuda.reset_peak_memory_stats()
    mem_before = torch.cuda.memory_allocated() / (1024**2)

t0 = time.perf_counter()
ra = RelateAnything.from_checkpoint(ckpt_path, device=device)
load_time = time.perf_counter() - t0

total_params = sum(p.numel() for p in ra.model.parameters())
trainable_params = sum(p.numel() for p in ra.model.parameters() if p.requires_grad)
mem_after_load = torch.cuda.memory_allocated() / (1024**2) if device == "cuda" else 0

print(f"Model Loaded in : {load_time:.2f} s")
print(f"Total Params    : {total_params:,} ({total_params / 1e6:.2f} M)")
print(f"Default Vocab   : {len(ra.predicates)} predicates")
print(f"Calibration     : a={ra.calib_a:.4f}, b={ra.calib_b:.4f}")
print(f"Model VRAM Load : {mem_after_load - mem_before:.2f} MB (Total allocated: {mem_after_load:.2f} MB)")

# Define test cases with arbitrary boxes [x1, y1, x2, y2] in normalized [0, 1] then scaled to W, H
test_cases = [
    {
        "name": "horse.jpg",
        "boxes_norm": [
            [0.36, 0.14, 0.51, 0.69],  # person / rider
            [0.10, 0.34, 0.78, 0.96],  # white horse
            [0.41, 0.39, 0.58, 0.58],  # white striped bag
            [0.37, 0.22, 0.47, 0.45],  # plaid shirt
            [0.34, 0.43, 0.44, 0.58],  # red saddle blanket
        ],
        "true_labels": ["person", "horse", "bag", "plaid_shirt", "saddle_cloth"],
        "fake_labels": ["banana", "spaceship", "toaster", "cloud", "pizza"],  # deliberately absurd to prove class-agnostic!
    },
    {
        "name": "catlaptop.jpg",
        "boxes_norm": [
            [0.25, 0.02, 0.89, 0.80],  # Siamese cat
            [0.24, 0.41, 0.84, 0.98],  # laptop computer
            [0.38, 0.72, 0.68, 0.89],  # laptop keyboard
            [0.00, 0.23, 0.99, 0.99],  # bed / sheet
        ],
        "true_labels": ["cat", "laptop", "keyboard", "bed"],
        "fake_labels": ["obj_A", "obj_B", "obj_C", "obj_D"],
    },
    {
        "name": "skateboard.jpg",
        "boxes_norm": [
            [0.25, 0.47, 0.31, 0.69],  # skater person
            [0.24, 0.66, 0.33, 0.71],  # electric skateboard
            [0.26, 0.50, 0.30, 0.57],  # backpack
            [0.26, 0.47, 0.29, 0.51],  # helmet
            [0.00, 0.61, 1.00, 0.99],  # street / road
        ],
        "true_labels": ["person", "skateboard", "backpack", "helmet", "road"],
        "fake_labels": ["region_0", "region_1", "region_2", "region_3", "region_4"],
    },
    {
        "name": "bicycle.jpg",
        "boxes_norm": [
            [0.38, 0.36, 0.58, 0.74],  # cyclist
            [0.35, 0.52, 0.60, 0.86],  # bicycle
            [0.38, 0.47, 0.48, 0.58],  # shorts
            [0.39, 0.36, 0.50, 0.51],  # t-shirt
            [0.00, 0.70, 1.00, 0.99],  # pavement / road
        ],
        "true_labels": ["cyclist", "bicycle", "shorts", "t-shirt", "road"],
        "fake_labels": ["box_0", "box_1", "box_2", "box_3", "box_4"],
    },
]

print("\n" + "=" * 70)
print("2. FUNCTIONAL & QUALITATIVE TEST (Default Vocabulary & Two-Graph Decompose)")
print("=" * 70)

for tc in test_cases:
    img_path = os.path.join(img_dir, tc["name"])
    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    boxes = np.array(tc["boxes_norm"], dtype=np.float32)
    boxes[:, [0, 2]] *= W
    boxes[:, [1, 3]] *= H

    # Standard prediction
    trips_true = ra.predict(img, boxes, box_labels=tc["true_labels"], topk=6)
    trips_fake = ra.predict(img, boxes, box_labels=tc["fake_labels"], topk=6)

    # Verify bit-for-bit identical scores and predicates between true labels and absurd fake labels
    scores_diff = max(abs(a.score - b.score) for a, b in zip(trips_true, trips_fake))
    preds_same = all(a.predicate == b.predicate and a.subject_idx == b.subject_idx and a.object_idx == b.object_idx
                     for a, b in zip(trips_true, trips_fake))

    print(f"\n--- Image: {tc['name']} ({W}x{H}, {len(boxes)} boxes) ---")
    print(f"[Class-Agnostic Proof] True vs Absurd Fake Labels -> Exact Same Predicates? {preds_same} (Max Score Diff: {scores_diff:.8f})")
    print("Top Ranked Relations:")
    for t in trips_true[:5]:
        print(f"  {t}")

    # Decompose into Spatial + Semantic graphs in 1 pass
    graphs = ra.predict(img, boxes, box_labels=tc["true_labels"], topk=3, decompose=True)
    print("Decomposed [Semantic / Interaction]:", ", ".join(str(t) for t in graphs["semantic"][:3]))
    print("Decomposed [Spatial / Layout]      :", ", ".join(str(t) for t in graphs["spatial"][:3]))

print("\n" + "=" * 70)
print("3. OPEN-VOCABULARY & FULL 19,103-PREDICATE BANK TEST")
print("=" * 70)

horse_img = Image.open(os.path.join(img_dir, "horse.jpg")).convert("RGB")
W, H = horse_img.size
horse_boxes = np.array(test_cases[0]["boxes_norm"], dtype=np.float32)
horse_boxes[:, [0, 2]] *= W
horse_boxes[:, [1, 3]] *= H
horse_labels = test_cases[0]["true_labels"]

# Custom open-vocabulary strings never seen as fixed classes
custom_preds = [
    "mounted on",
    "straddling and riding",
    "carrying on shoulder",
    "draped over the back of",
    "dressed in",
    "eating",
    "repairing",
]
t_voc = time.perf_counter()
ra.set_vocabulary(custom_preds)
voc_ms = (time.perf_counter() - t_voc) * 1000
print(f"[Custom Open-Vocab] Encoded {len(custom_preds)} arbitrary strings via Text Student in {voc_ms:.1f} ms:")
for t in ra.predict(horse_img, horse_boxes, box_labels=horse_labels, topk=5):
    print(f"  {t}")

# Load full 19,103 training vocabulary from sidecar predicate_embeddings.npz
t_full = time.perf_counter()
ra_full = RelateAnything.from_checkpoint(ckpt_path, device=device, full_vocabulary=True)
full_load_ms = (time.perf_counter() - t_full) * 1000
print(f"\n[Full 19,103 Vocabulary] Loaded {len(ra_full.predicates):,} predicates in {full_load_ms:.1f} ms:")
for t in ra_full.predict(horse_img, horse_boxes, box_labels=horse_labels, topk=5):
    print(f"  {t}")

# Cat on laptop with full 19,103 vocabulary
cat_img = Image.open(os.path.join(img_dir, "catlaptop.jpg")).convert("RGB")
Wc, Hc = cat_img.size
cat_boxes = np.array(test_cases[1]["boxes_norm"], dtype=np.float32)
cat_boxes[:, [0, 2]] *= Wc
cat_boxes[:, [1, 3]] *= Hc
print(f"\n[Full 19,103 Vocabulary on catlaptop.jpg]:")
for t in ra_full.predict(cat_img, cat_boxes, box_labels=test_cases[1]["true_labels"], topk=5):
    print(f"  {t}")

print("\n" + "=" * 70)
print("4. LATENCY & VRAM BENCHMARK (PyTorch FP32 vs FP16, Default vs 19,103 Vocab)")
print("=" * 70)

# Restore default vocab on `ra`
from relsgg.vocabulary import DEFAULT_PREDICATES
ra.set_vocabulary(DEFAULT_PREDICATES)

# Create synthetic 15-box test input for realistic crowded scene benchmarking
np.random.seed(42)
b15 = np.sort(np.random.uniform(50, 800, size=(15, 4)).astype(np.float32), axis=1)
b15[:, 2] = np.clip(b15[:, 0] + np.random.uniform(50, 300, size=15), 0, W)
b15[:, 3] = np.clip(b15[:, 1] + np.random.uniform(50, 300, size=15), 0, H)

def bench_model(model_obj, desc, n_warmup=5, n_iters=30, use_amp=False):
    if device == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    for _ in range(n_warmup):
        if use_amp:
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                model_obj.predict(horse_img, b15, topk=20)
        else:
            model_obj.predict(horse_img, b15, topk=20)
    if device == "cuda":
        torch.cuda.synchronize()
    times = []
    for _ in range(n_iters):
        t_start = time.perf_counter()
        if use_amp:
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                model_obj.predict(horse_img, b15, topk=20)
        else:
            model_obj.predict(horse_img, b15, topk=20)
        if device == "cuda":
            torch.cuda.synchronize()
        times.append((time.perf_counter() - t_start) * 1000)
    peak_mb = torch.cuda.max_memory_allocated() / (1024**2) if device == "cuda" else 0
    med = np.median(times)
    mean = np.mean(times)
    p95 = np.percentile(times, 95)
    print(f"{desc:42s} | Median: {med:6.2f} ms ({1000/med:5.1f} FPS) | Mean: {mean:6.2f} ms | P95: {p95:6.2f} ms | Peak VRAM: {peak_mb:6.1f} MB")

bench_model(ra, f"FP32 ({len(ra.predicates)} predicates, 15 boxes)", use_amp=False)
bench_model(ra_full, f"FP32 ({len(ra_full.predicates):,} predicates, 15 boxes)", use_amp=False)
if device == "cuda":
    bench_model(ra, f"FP16 AMP ({len(ra.predicates)} predicates, 15 boxes)", use_amp=True)
    bench_model(ra_full, f"FP16 AMP ({len(ra_full.predicates):,} predicates, 15 boxes)", use_amp=True)
