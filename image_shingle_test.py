
import os
import pandas as pd
import json
import statistics
from pathlib import Path
import yaml
import matplotlib.pyplot as plt
import matplotlib as mpl
from filelock import FileLock
from crawler import CrawlResults, CrawlDataEncoder
from utils.utils import get_directories, get_domain
from utils.image_shingle import ImageShingle
import time

blue = ImageShingle("testcases/blue.png")
green = ImageShingle("testcases/green.png")
green_blue = ImageShingle("testcases/green-blue.png")
green_left_blemish = ImageShingle("testcases/green-left-blemish.png")
green_right_blemish = ImageShingle("testcases/green-right-blemish.png")

# Baseline, control, experimental
print("Same Baseline and Control")
print("Expected 0")
print(ImageShingle.compare_with_control(green, green, blue))
print("Expected 0.5")
print(ImageShingle.compare_with_control(green, green, green_blue))
print("Expected 1")
print(ImageShingle.compare_with_control(green, green, green))
print()

print("Completely different Baseline and Control")
print("Expected exception")
try:
    ImageShingle.compare_with_control(green, blue, green)
except Exception as e:
    print(e)
print()

print("Half different Baseline and Control")
print("Expected 1")
print(ImageShingle.compare_with_control(green, green_blue, green_right_blemish))
print("Expected < 1")
print(ImageShingle.compare_with_control(green, green_blue, green_left_blemish))