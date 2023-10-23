from utils import open_file, time_to_seconds, extract_frames
import os
import glob
import torch
import torchvision.transforms as transforms
import clip
import PIL
from PIL import Image
import numpy as np
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
import json
import pytube
from pytube import YouTube

torch.set_num_threads(2)

list_of_annotations = glob.glob('../multisum_data/annotation/*/*/*')

# Load the CLIP model
device = "cuda:0" if torch.cuda.is_available() else "cpu"
#model, preprocess = clip.load('ViT-B/32', device=device)

# Modify the model to output features of size 2048
#model.visual.output_dim = 2048

# Define the transform to preprocess the input frames
#transform = transforms.Compose([
    #transforms.Resize(224),
    #transforms.CenterCrop(224),
    #preprocess
#])


class VideoFramesDataset(Dataset):
    def __init__(self, frames, transform):
        self.frames = frames
        self.transform = transform

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, idx):
        frame = self.frames[idx]
        preprocessed_frame = self.transform(Image.fromarray(frame))
        return preprocessed_frame


linear = torch.nn.Linear(512, 2048, dtype=torch.float16).to(device)
#model.to(device)

save_np_dic = {}

batch_size = 128

corrupted_videos = []

count = 0

for annotation in tqdm(list_of_annotations, desc='Extracting features: '):

    json_file = open_file(annotation)
    id = json_file['info']['video_id']
    keyframes = json_file['summary']

    start_time_seconds = 0
    end_time_seconds = time_to_seconds(json_file['info']['duration'])
    # print(json_file)
    if not os.path.exists(f"../multisum_data/video/{json_file['info']['category']}"):
        os.mkdir(f"../multisum_data/video/{json_file['info']['category']}")
    if not os.path.exists(
            f"../multisum_data/video/{json_file['info']['category']}/{json_file['info']['sub_category']}"):
        os.mkdir(f"../multisum_data/video/{json_file['info']['category']}/{json_file['info']['sub_category']}")
    video_url = json_file['info']['url']
    yt = YouTube(video_url)
    fail_list = []
    try:
        yt.streams.filter(file_extension='mp4').first().download(
            output_path=f"../multisum_data/video/{json_file['info']['category']}/{json_file['info']['sub_category']}",
            filename=json_file['info']['video_id'] + '.mp4')
    except:
        fail_list.append(id)
print(len(fail_list))
with open('fail.json','w') as fw:
    json.dump(fail_list,fw)
