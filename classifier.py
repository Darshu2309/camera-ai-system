import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

device = "cuda" if torch.cuda.is_available() else "cpu"

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# 🔥 IMPROVED LABELS
labels = [
    "person",
    "mobile phone",
    "bottle",
    "laptop",
    "bag",
    "backpack",
    "chair",
    "table",
    "vehicle",
    "car",
    "bike",
    "animal",
    "dog",
    "cat",
    "weapon",
    "gun",
    "knife"
]

def classify_object(frame, bbox):
    x1, y1, x2, y2 = bbox
    crop = frame[y1:y2, x1:x2]

    # ✅ FIX: avoid crash
    if crop.size == 0:
        return "unknown", 0.0

    image = Image.fromarray(crop)

    inputs = processor(
        text=labels,
        images=image,
        return_tensors="pt",
        padding=True
    ).to(device)

    outputs = model(**inputs)
    probs = outputs.logits_per_image.softmax(dim=1)

    idx = probs.argmax().item()
    confidence = float(probs[0][idx])

    # 🔥 CONFIDENCE FILTER
    if confidence < 0.3:
        return "unknown", confidence

    return labels[idx], confidence