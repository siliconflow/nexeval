import os
from typing import Dict, List, Optional, Tuple, Union

import clip
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from T2IBenchmark.model_wrapper import T2IModelWrapper, ModelWrapperDataloader
from T2IBenchmark.feature_extractors import BaseFeatureExtractor, InceptionV3FE
from T2IBenchmark.loaders import (
    BaseImageLoader,
    CaptionImageDataset,
    ImageDataset,
    get_images_from_folder,
    validate_image_paths,
)
from T2IBenchmark.datasets import get_coco_30k_captions, get_coco_fid_stats
from T2IBenchmark.metrics import FIDStats, frechet_distance
from T2IBenchmark.utils import dprint, set_all_seeds


def create_dataset_from_input(
        obj: Union[str, List[str], BaseImageLoader, FIDStats]
) -> Union[BaseImageLoader, FIDStats]:
    if isinstance(obj, str):
        if obj.endswith(".npz"):
            # fid statistics
            return FIDStats.from_npz(obj)
        else:
            # path to folder
            image_paths = get_images_from_folder(obj)
            dataset = ImageDataset(image_paths)
            return dataset
    elif isinstance(obj, list):
        # list of paths
        validate_image_paths(obj)
        dataset = ImageDataset(obj)
        return dataset
    elif isinstance(obj, BaseImageLoader):
        return obj
    elif isinstance(obj, FIDStats):
        return obj
    else:
        raise ValueError(f"Input {obj} has unknown type. See the documentation")


def get_features_for_dataset(
    dataset: BaseImageLoader,
    feature_extractor: BaseFeatureExtractor,
    verbose: bool = True,
) -> np.ndarray:
    features = []
    for x in tqdm(dataset, disable=not verbose):
        feats = feature_extractor.forward(x).numpy()
        features.append(feats)

    res_feats = np.concatenate(features)
    return res_feats


def calculate_fid(
    input1: Union[str, List[str], BaseImageLoader, FIDStats],
    input2: Union[str, List[str], BaseImageLoader, FIDStats],
    device: torch.device = 'cuda',
    seed: Optional[int] = 42,
    batch_size: int = 128,
    dataloader_workers: int = 16,
    verbose: bool = True,
) -> (int, Tuple[dict, dict]):
    """
    Calculate the Frechet Inception Distance (FID) between two sets of images.

    Parameters
    ----------
    input1 : Union[str, List[str], BaseImageLoader]
        The first set of images to compute the FID score for. This can either be
        a path to directory, a path to .npz file, a list of image file paths, an instance
        of BaseImageLoader or an instance of FIDStats.
    input2 : Union[str, List[str], BaseImageLoader]
        The second set of images to compute the FID score for. This can either be
        a path to directory, a path to .npz file, a list of image file paths, an instance
        of BaseImageLoader or an instance of FIDStats.
    device : torch.device, optional, default='cuda'
        The device to perform the calculations on, by default 'cuda'.
    seed : int, optional, default=42
        The seed value to ensure reproducibility, by default 42.
    batch_size : int, optional, default=128
        The batch size to use for processing the images, by default 128.
    dataloader_workers : int, optional, default=16
        The number of workers for data loading, by default 16.
    verbose : bool, optional, default=True
        Whether to print progress information, by default True.

    Returns
    -------
    int
        The computed FID score.
    Tuple[dict, dict]
        Two dictionaries containing the features and statistics of input1 and input2, respectively.
    """
    if seed:
        set_all_seeds(seed)

    input1 = create_dataset_from_input(input1)
    input2 = create_dataset_from_input(input2)

    # create inception net
    inception_fe = InceptionV3FE(device)

    stats = []
    all_features = []
    # process inputs
    for input_data in [input1, input2]:
        dprint(verbose, f"Processing: {input_data}")
        if isinstance(input_data, FIDStats):
            all_features.append([])
            stats.append(input_data)
        elif isinstance(input_data, ImageDataset):
            # if a dataset-like
            dataset = input_data
            dataset.preprocess_fn = inception_fe.get_preprocess_fn()
            dataloader = DataLoader(
                dataset,
                batch_size=batch_size,
                shuffle=False,
                drop_last=False,
                num_workers=dataloader_workers,
            )
            features = get_features_for_dataset(
                dataloader, inception_fe, verbose=verbose
            )
            all_features.append(features)
            stats.append(FIDStats.from_features(features))
        elif isinstance(input_data, T2IModelWrapper):
            dataloader = ModelWrapperDataloader(input_data, batch_size, preprocess_fn=inception_fe.get_preprocess_fn())
            features = get_features_for_dataset(dataloader, inception_fe, verbose=verbose)
            all_features.append(features)
            stats.append(FIDStats.from_features(features))
            
    fid = frechet_distance(stats[0], stats[1])
    dprint(verbose, f"FID is {fid}")
    return fid, (
        {"features": all_features[0], "stats": stats[0]},
        {"features": all_features[1], "stats": stats[1]},
    )


def calculate_coco_fid(
    ModelWrapper: T2IModelWrapper,
    device: torch.device = 'cuda',
    seed: Optional[int] = 42,
    batch_size: int = 1,
    save_generations_dir: str = 'coco_generations/'
) -> (int, Tuple[dict, dict]):
    os.makedirs(save_generations_dir, exist_ok=True)
    # get COCO-30k captions
    id2caption = get_coco_30k_captions()
    captions = []
    ids = []
    for d in id2caption.items():
        ids.append(d[0])
        captions.append(d[1])
        
    # init model
    model = ModelWrapper(device, save_dir=save_generations_dir, use_saved_images=True, seed=seed)
    model.set_captions(captions, file_ids=ids)
    
    # get coco FID stats
    coco_stats = get_coco_fid_stats()
    
    return calculate_fid(coco_stats, model, device=device, seed=seed, batch_size=batch_size)


def calculate_clip_score(
    image_paths: List[str],
    captions_mapping: Dict[str, str],
    device: torch.device = "cuda",
    seed: Optional[int] = 42,
    batch_size: int = 128,
    dataloader_workers: int = 16,
    verbose: bool = True,
):
    if seed:
        set_all_seeds(seed)

    model, preprocess = clip.load("ViT-B/32", device=device)
    dataset = CaptionImageDataset(
        images_paths=image_paths,
        captions=list(map(lambda x: captions_mapping[x], image_paths)),
        preprocess_fn=preprocess,
    )
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        drop_last=False,
        num_workers=dataloader_workers,
    )

    score_acc = 0.0
    num_samples = 0.0

    for image, caption in tqdm(dataloader):
        image_embedding = model.encode_image(image.to(device))
        caption_embedding = model.encode_text(clip.tokenize(caption).to(device))

        image_features = image_embedding / image_embedding.norm(dim=1, keepdim=True).to(
            torch.float32
        )
        caption_features = caption_embedding / caption_embedding.norm(
            dim=1, keepdim=True
        ).to(torch.float32)

        score = (image_features * caption_features).sum()
        score_acc += score
        num_samples += image.shape[0]

    clip_score = score_acc / num_samples
    dprint(verbose, f"CLIP score is {clip_score}")

    return clip_score
