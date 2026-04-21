"""
AgroBot — Rover Path Detection Service
Lightweight U-Net (PyTorch) for path segmentation on rover camera frames.
"""
import os
import io
import base64
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
IMG_SIZE  = 128

_model = None


# ---- Model definition (must match training) ----

def _build_model():
    import torch
    import torch.nn as nn

    class ConvBlock(nn.Module):
        def __init__(self, in_ch, out_ch):
            super().__init__()
            self.block = nn.Sequential(
                nn.Conv2d(in_ch, out_ch, 3, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_ch, out_ch, 3, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(inplace=True),
            )
        def forward(self, x): return self.block(x)

    class UNet(nn.Module):
        def __init__(self, filters=(16, 32, 64, 128)):
            super().__init__()
            f = filters
            self.enc1 = ConvBlock(3,    f[0])
            self.enc2 = ConvBlock(f[0], f[1])
            self.enc3 = ConvBlock(f[1], f[2])
            self.bridge = nn.Sequential(ConvBlock(f[2], f[3]),
                                        nn.Dropout2d(0.3))
            self.up3  = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
            self.dec3 = ConvBlock(f[3] + f[2], f[2])
            self.up2  = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
            self.dec2 = ConvBlock(f[2] + f[1], f[1])
            self.up1  = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
            self.dec1 = ConvBlock(f[1] + f[0], f[0])
            self.pool = nn.MaxPool2d(2)
            self.out  = nn.Conv2d(f[0], 1, 1)

        def forward(self, x):
            c1 = self.enc1(x);  p1 = self.pool(c1)
            c2 = self.enc2(p1); p2 = self.pool(c2)
            c3 = self.enc3(p2); p3 = self.pool(c3)
            cb = self.bridge(p3)
            d3 = self.dec3(torch.cat([self.up3(cb), c3], dim=1))
            d2 = self.dec2(torch.cat([self.up2(d3), c2], dim=1))
            d1 = self.dec1(torch.cat([self.up1(d2), c1], dim=1))
            return torch.sigmoid(self.out(d1))

    return UNet()


def _load():
    global _model
    if _model is None:
        try:
            import torch
            weights_path = os.path.join(MODEL_DIR, 'path_model.pt')
            net = _build_model()
            net.load_state_dict(torch.load(weights_path, map_location='cpu'))
            net.eval()
            _model = net
            print('[path_detection] Path model loaded.')
        except Exception as e:
            print(f'[path_detection] Could not load model: {e}')


def _preprocess(image_bytes):
    import torch
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB').resize((IMG_SIZE, IMG_SIZE))
    arr = np.array(img, dtype=np.float32) / 255.0       # (H, W, 3)
    arr = arr.transpose(2, 0, 1)[np.newaxis]             # (1, 3, H, W)
    return torch.from_numpy(arr)


def _mask_to_direction(mask_np):
    """Derive steering command from binary path mask (H×W numpy array)."""
    binary = (mask_np > 0.5).astype(np.uint8)
    h, w   = binary.shape
    roi    = binary[int(h * 0.4):, :]
    col_sums = roi.sum(axis=0)
    path_cols = np.where(col_sums > roi.shape[0] * 0.12)[0]

    if len(path_cols) == 0:
        return 'STOP', 0.0

    offset = (float(path_cols.mean()) - w / 2.0) / (w / 2.0)

    if   offset < -0.2: direction = 'LEFT'
    elif offset >  0.2: direction = 'RIGHT'
    else:               direction = 'STRAIGHT'

    coverage = round(float(binary.sum()) / binary.size * 100, 1)
    return direction, coverage


def _mask_to_base64(mask_np):
    from PIL import Image
    img = Image.fromarray((mask_np * 255).astype(np.uint8), mode='L')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def predict_path(image_bytes):
    """
    Run path detection on raw image bytes.
    Returns direction, coverage %, and base64 mask PNG.
    """
    _load()
    if _model is None:
        return {
            'direction': 'UNKNOWN',
            'coverage':  0,
            'mask_base64': None,
            'error': 'Path model not loaded — run AI Model/path_detection.ipynb first',
        }

    import torch
    inp = _preprocess(image_bytes)
    with torch.no_grad():
        raw = _model(inp)[0, 0].numpy()          # (H, W)

    direction, coverage = _mask_to_direction(raw)
    return {
        'direction':    direction,
        'coverage':     coverage,
        'mask_base64':  _mask_to_base64(raw),
    }
