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

torch.set_num_threads(4)

list_of_annotations = glob.glob('../multisum_data/annotation/animals/*/*')

# Load the CLIP model
device = "cuda:0" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load('ViT-B/32', device=device)

# Modify the model to output features of size 2048
model.visual.output_dim = 2048

# Define the transform to preprocess the input frames
transform = transforms.Compose([
    transforms.Resize(224),
    transforms.CenterCrop(224),
    preprocess
])


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
model.to(device)

save_np_dic = {}

batch_size = 128

corrupted_videos = []

count_1 = 0


for annotation in tqdm(list_of_annotations, desc = 'Extracting features: '):
    
    json_file = open_file(annotation)
    id = json_file['info']['video_id']
    keyframes = json_file['summary']
    
    start_time_seconds = 0
    end_time_seconds = time_to_seconds(json_file['info']['duration'])

    path_to_video = f"../multisum_data/video/{json_file['info']['category']}/{json_file['info']['sub_category']}/{json_file['info']['video_id']}.mp4"
    frames = extract_frames(path_to_video, start_time_seconds, end_time_seconds, 100)
    frames = frames[:99]
    # print(len(frames))
    count = 0
    if len(frames) == 0:
        corrupted_videos.append(path_to_video)
        print('Corrupted ... ')
        pass
    else:

        dataset = VideoFramesDataset(frames, transform)

        dataloader = DataLoader(dataset, batch_size=99, shuffle=False)

        features_list = []
        with torch.no_grad():
            for batch in dataloader:
                batch = batch.to(device)
            
                
                # image.save(f'image_{count}_{count_1}.png')
                features = model.encode_image(batch)
                features = linear(features.to(device))
                features_list.append(features.cpu())
                count +=1
        features = torch.cat(features_list, dim=0)
        assert(features.shape[0] == len(frames))
        np.save(f'MLASK/src/data/videos_frame/{id}.npy', features.numpy())
        # print(frames)
        np.save(f'MLASK/src/data/frames/{id}.npy', frames)
        del frames
        del features
        # save_np_dic[f'{id}'] = features.numpy()

    # count +=1 
    
    # if count == 50:
    #     break
# The features tensor has shape [num_frames, feature_size]
with open('corrupted_videos.json', 'w') as f:
    json.dump(corrupted_videos, f)

# np.save('msmo_clip_features.npy', save_np_dic)