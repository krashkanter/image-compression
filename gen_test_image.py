import cv2
import numpy as np

# Create a 64x64 grayscale image
# Make it interesting so it doesn't compress to trivial single block (though 64x64 is small)
img = np.zeros((64, 64), dtype=np.uint8)
# Gradient
for i in range(64):
    for j in range(64):
        img[i, j] = (i + j) * 2

# Add some shapes
cv2.rectangle(img, (10, 10), (30, 30), 255, -1)
cv2.circle(img, (40, 40), 10, 128, -1)

cv2.imwrite('images/small_test.png', img)
print("Created images/small_test.png")
