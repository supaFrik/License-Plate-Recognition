import torch
import cv2
import numpy as np
from PIL import Image

print("Torch:", torch.__version__)

img = np.zeros((32,32,3), dtype=np.uint8)
print("Image shape:", img.shape)
