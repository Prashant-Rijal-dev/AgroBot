"""
AgroBot — Path Detection Model Training Script
Run: python "AI Model/train_path_model.py"
Saves: website/models/path_model.pt
"""
import numpy as np
import os, shutil, sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split

np.random.seed(42)
torch.manual_seed(42)

DEVICE     = 'cuda' if torch.cuda.is_available() else 'cpu'
IMG_SIZE   = 128
N_SAMPLES  = 1000
BATCH_SIZE = 32
EPOCHS     = 30
LR         = 1e-3
PATIENCE   = 7

print(f'PyTorch {torch.__version__} | device: {DEVICE}')

# ── Synthetic data ──────────────────────────────────────────────────────────

def generate_sample(size=IMG_SIZE):
    img  = np.zeros((size, size, 3), dtype=np.uint8)
    mask = np.zeros((size, size),    dtype=np.uint8)

    # Crop background
    img[:, :, 1] = np.random.randint(55, 110, (size, size), dtype=np.uint8)
    img[:, :, 0] = np.random.randint(15,  50, (size, size), dtype=np.uint8)
    img[:, :, 2] = np.random.randint(10,  40, (size, size), dtype=np.uint8)
    for x in range(0, size, np.random.randint(8, 18)):
        w = np.random.randint(1, 4)
        x1, x2 = max(0, x - w), min(size, x + w)
        img[:, x1:x2, 1] = np.clip(img[:, x1:x2, 1].astype(int) - 20, 0, 255).astype(np.uint8)

    # Dirt path strip
    pw = np.random.randint(22, 55)
    cx = np.random.randint(pw // 2 + 5, size - pw // 2 - 5)
    for row in range(size):
        cx = int(np.clip(cx + np.random.normal(0, 1.2), pw // 2, size - pw // 2))
        l, r = max(0, cx - pw // 2), min(size, cx + pw // 2)
        w = r - l
        img[row, l:r, 0] = np.random.randint(100, 155, w, dtype=np.uint8)
        img[row, l:r, 1] = np.random.randint(80,  120, w, dtype=np.uint8)
        img[row, l:r, 2] = np.random.randint(50,   90, w, dtype=np.uint8)
        mask[row, l:r] = 1

    alpha = np.random.uniform(0.7, 1.3)
    beta  = np.random.randint(-20, 20)
    img   = np.clip(img.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)
    return img, mask


class PathDataset(Dataset):
    def __init__(self, n):
        print(f'  generating {n} samples...', end=' ', flush=True)
        imgs, msks = [], []
        for i in range(n):
            img, mask = generate_sample()
            imgs.append(img.astype(np.float32).transpose(2, 0, 1) / 255.0)
            msks.append(mask.astype(np.float32)[np.newaxis])
            if (i + 1) % 200 == 0:
                print(f'{i+1}', end=' ', flush=True)
        self.images = np.stack(imgs)
        self.masks  = np.stack(msks)
        print('done.')
    def __len__(self): return len(self.images)
    def __getitem__(self, i):
        return torch.from_numpy(self.images[i]), torch.from_numpy(self.masks[i])


print(f'Generating {N_SAMPLES} samples...', end=' ', flush=True)
ds = PathDataset(N_SAMPLES)
print('done.')
val_n = int(N_SAMPLES * 0.15)
train_ds, val_ds = random_split(ds, [N_SAMPLES - val_n, val_n])
train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
print(f'Train: {len(train_ds)}  Val: {len(val_ds)}')

# ── Model ───────────────────────────────────────────────────────────────────

class ConvBlock(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
        )
    def forward(self, x): return self.block(x)

class UNet(nn.Module):
    def __init__(self, f=(16, 32, 64, 128)):
        super().__init__()
        self.enc1   = ConvBlock(3, f[0]);   self.enc2 = ConvBlock(f[0], f[1])
        self.enc3   = ConvBlock(f[1], f[2])
        self.bridge = nn.Sequential(ConvBlock(f[2], f[3]), nn.Dropout2d(0.3))
        self.up3    = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.dec3   = ConvBlock(f[3]+f[2], f[2])
        self.up2    = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.dec2   = ConvBlock(f[2]+f[1], f[1])
        self.up1    = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.dec1   = ConvBlock(f[1]+f[0], f[0])
        self.pool   = nn.MaxPool2d(2)
        self.out    = nn.Conv2d(f[0], 1, 1)

    def forward(self, x):
        c1=self.enc1(x);  p1=self.pool(c1)
        c2=self.enc2(p1); p2=self.pool(c2)
        c3=self.enc3(p2); p3=self.pool(c3)
        cb=self.bridge(p3)
        d3=self.dec3(torch.cat([self.up3(cb), c3], 1))
        d2=self.dec2(torch.cat([self.up2(d3), c2], 1))
        d1=self.dec1(torch.cat([self.up1(d2), c1], 1))
        return torch.sigmoid(self.out(d1))

model = UNet().to(DEVICE)
print(f'Parameters: {sum(p.numel() for p in model.parameters()):,}')

# ── Loss / metrics ──────────────────────────────────────────────────────────

def dice_loss(p, t, s=1e-6):
    p=p.view(-1); t=t.view(-1)
    return 1-(2*(p*t).sum()+s)/(p.sum()+t.sum()+s)

def loss_fn(p, t): return nn.functional.binary_cross_entropy(p, t) + dice_loss(p, t)

def iou(p, t):
    p=(p>0.5).float(); i=(p*t).sum(); u=p.sum()+t.sum()-i
    return (i/(u+1e-6)).item()

# ── Training ─────────────────────────────────────────────────────────────────

opt  = optim.Adam(model.parameters(), lr=LR)
sched = optim.lr_scheduler.ReduceLROnPlateau(opt, mode='max', factor=0.5, patience=3)
best_iou, patience_cnt = 0.0, 0

for ep in range(1, EPOCHS+1):
    model.train()
    t_loss = 0.0
    for imgs, masks in train_loader:
        imgs, masks = imgs.to(DEVICE), masks.to(DEVICE)
        opt.zero_grad()
        loss = loss_fn(model(imgs), masks)
        loss.backward(); opt.step()
        t_loss += loss.item()
    t_loss /= len(train_loader)

    model.eval()
    v_iou = 0.0
    with torch.no_grad():
        for imgs, masks in val_loader:
            v_iou += iou(model(imgs.to(DEVICE)), masks.to(DEVICE))
    v_iou /= len(val_loader)
    sched.step(v_iou)

    if v_iou > best_iou:
        best_iou = v_iou
        torch.save(model.state_dict(), '/tmp/best_path_model.pt')
        patience_cnt = 0
    else:
        patience_cnt += 1

    print(f'Ep {ep:3d}/{EPOCHS}  loss={t_loss:.4f}  val_IoU={v_iou*100:.1f}%  best={best_iou*100:.1f}%')

    if patience_cnt >= PATIENCE:
        print(f'Early stopping at epoch {ep}')
        break

# ── Save ─────────────────────────────────────────────────────────────────────

script_dir = os.path.dirname(os.path.abspath(__file__))
model_dir  = os.path.join(script_dir, '..', 'website', 'models')
os.makedirs(model_dir, exist_ok=True)
dst = os.path.join(model_dir, 'path_model.pt')
shutil.copy('/tmp/best_path_model.pt', dst)

print(f'\nModel saved → {dst}  ({os.path.getsize(dst)/1024:.0f} KB)')
print(f'Best Val IoU : {best_iou*100:.1f}%')
