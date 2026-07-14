import torch


def get_device() -> torch.device:
    """
    Return the best available device for PyTorch.
    """

    if torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


if __name__ == "__main__":

    device = get_device()

    print(f"Using device: {device}")