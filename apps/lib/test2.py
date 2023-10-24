import cv2
import os
import numpy as np
import math
import re


def next_square(num):
    sqrt_num = math.isqrt(num)
    if sqrt_num ** 2 == num:
        return num
    else:
        return (sqrt_num + 1) ** 2

path = os.path.abspath(os.path.dirname(__file__))

print(f"Pth: {path}\t Type: {type(path)}")
path_img = os.path.join(path, "img")

#get list of names of the files inside path img
# jpg_list = [os.path.join(path_img, f) for f in os.listdir(path_img) if f.endswith('.jpg')]
jpg_list = [os.path.join(path_img, f) for f in os.listdir(path_img) if re.match(r"img_\d+\.jpg", f)]
for f in jpg_list:
    print(f)


#read images
img_list = []
for img in jpg_list:
    img_list.append(cv2.imread(img))

print(len(img_list))

# join row
img_side_by_side = np.concatenate(img_list, axis=1)

# make a matriz of images
n_matriz = np.sqrt(next_square(len(img_list))).astype(int)
img_matrix = np.zeros((n_matriz, n_matriz), dtype=object)

# put images in the matrix
for i in range(n_matriz):
    for j in range(n_matriz):
        img_matrix[i, j] = img_list[i*n_matriz + j]

# Join rows
img_rows = []
for row in img_matrix:
    img_rows.append(np.concatenate(row, axis=1))
img_concatenated = np.concatenate(img_rows, axis=0)

# show image
# cv2.imshow("image", img_concatenated)
# cv2.waitKey(0)

# cv2.imshow("image", img_side_by_side)
# cv2.waitKey(0)

# save image in img path
cv2.imwrite(os.path.join(path_img, "img_matrix.jpg"), img_concatenated)
cv2.imwrite(os.path.join(path_img, "img_row.jpg"), img_side_by_side)

