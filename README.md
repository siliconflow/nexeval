# OneDiffGenMetrics


This repository is used for evaluating the quality of generation after compilation acceleration using [OneDiff](https://github.com/siliconflow/onediff).

## Quick Start

1. **Prepare the OneDiff environment.**

    Follow the instructions to install OneDiff and other dependencies. 
- [Community Edition (CE)](https://github.com/siliconflow/onediff/tree/main?tab=readme-ov-file#installation)
- [Enterprise Edition (EE)](https://github.com/siliconflow/onediff/blob/main/README_ENTERPRISE.md#diffusers-with-onediff-enterprise)

2. **Benchmark environment.**

    ```
    # Method 1: Pypi download and install
    pip install hpsv2

    # Method 2: install locally
    git clone https://github.com/tgxs002/HPSv2.git
    cd HPSv2
    pip install -e . 

    # Optional: images for reproducing our benchmark will be downloaded here
    # default: ~/.cache/hpsv2/
    export HPS_ROOT=/your/cache/path
    ```
 
### SDXL
Run:
```
bash run_sdxl_tests.sh
```

Results:

| Optimization Technique | Paintings Score | Photo Score | Concept-Art Score | Anime Score | Average Score | Inference Time (s) for 30 Steps, 1024*1024 |
|------------------------|-----------------|-------------|-------------------|-------------|---------------|--------------------------------|
| OneDiff Quant + DeepCache (EE)     | 28.51 ± 0.4962  | 26.91 ± 0.4605 | 28.42 ± 0.3953  | 30.50 ± 0.3470 | 28.58         | 3057.66                        |
| OneDiff Quant (EE)                    | 30.05 ± 0.3897  | 28.26 ± 0.4339 | 30.04 ± 0.3807  | 31.79 ± 0.3224 | 30.04         | 7068.45                        |
| DeepCache (CE)              | 28.45 ± 0.3816  | 27.03 ± 0.3348 | 28.56 ± 0.3517  | 30.49 ± 0.3626 | 28.63         | 3634.66                        |
| OneDiff Compile (CE)                | 30.07 ± 0.3789  | 28.42 ± 0.2491 | 30.17 ± 0.2834  | 31.73 ± 0.3485 | 30.10         | 9043.38                        |
| Pytorch                  | 30.07 ± 0.3887  | 28.43 ± 0.2726 | 30.16 ± 0.2686  | 31.74 ± 0.3691 | 30.10         | 13335.64                       |



### References

- Wu, X., Hao, Y., Sun, K., Chen, Y., Zhu, F., Zhao, R., & Li, H. (2023). Human Preference Score v2: A Solid Benchmark for Evaluating Human Preferences of Text-to-Image Synthesis. arXiv preprint arXiv:2306.09341.
