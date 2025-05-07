import argparse
import os
from pathlib import Path
from tqdm import tqdm
import cv2
import io
import base64
from PIL import Image
import numpy as np


def ndarray_to_base64(image_np: np.ndarray, ext='.jpg', scale=0.25) -> str:
    prefix = "data:image/jpeg;base64,"
    if scale != 1:
        image_np = cv2.resize(image_np, None, fx=scale, fy=scale)
    # 将ndarray编码成指定格式的图片内存缓冲区
    success, encoded_image = cv2.imencode(ext, image_np)
    if not success:
        raise ValueError("图像编码失败")
    # 转换为bytes并进行base64编码
    base64_bytes = base64.b64encode(encoded_image.tobytes())
    # 转换为字符串返回
    base64_str = prefix + base64_bytes.decode('utf-8')
    return base64_str

def _encode_image(img: Image):
    """Encode image as base64"""
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    base64_image = base64.b64encode(
        img_byte_arr.getvalue()
        ).decode('utf-8')
    return base64_image


def _similarity_score(previous_frame_np: np.ndarray, current_frame_np: np.ndarray):
    """
    SSIM by Z. Wang: https://ece.uwaterloo.ca/~z70wang/research/ssim/
    Paper:  Z. Wang, A. C. Bovik, H. R. Sheikh and E. P. Simoncelli,
    "Image quality assessment: From error visibility to structural similarity," IEEE Transactions on Image Processing, vol. 13, no. 4, pp. 600-612, Apr. 2004.
    """
    # previous_frame_np = np.array(previous_frame_img.convert('L'))
    # current_frame_np = np.array(current_frame_img.convert('L'))

    K1 = 0.005
    K2 = 0.015
    L = 255

    C1 = (K1 * L) ** 2
    C2 = (K2 * L) ** 2

    # previous_frame_np = np.array(previous_frame_img)
    # current_frame_np = np.array(current_frame_gray)

    # Ensure both frames have same dimensions
    if previous_frame_np.shape != current_frame_np.shape:
        min_shape = np.minimum(
            previous_frame_np.shape, current_frame_np.shape)
        previous_frame_np = previous_frame_np[:min_shape[0], :min_shape[1]]
        current_frame_np = current_frame_np[:min_shape[0], :min_shape[1]]

    # Calculate mean (mu)
    mu1 = np.mean(previous_frame_np, dtype=np.float64)
    mu2 = np.mean(current_frame_np, dtype=np.float64)

    # Calculate variance (sigma^2) and covariance (sigma12)
    sigma1_sq = np.var(previous_frame_np, dtype=np.float64)#, mean=mu1)
    sigma2_sq = np.var(current_frame_np, dtype=np.float64)#, mean=mu2)
    sigma12 = np.cov(previous_frame_np.flatten(),
                        current_frame_np.flatten(),
                        dtype=np.float64)[0, 1]

    # Calculate SSIM
    ssim = ((2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)) / \
        ((mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2))

    return ssim