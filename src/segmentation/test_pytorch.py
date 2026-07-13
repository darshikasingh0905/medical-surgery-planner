import torch

print("PyTorch Version:", torch.__version__)

print("CUDA Available:", torch.cuda.is_available())

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Using Device:", device)

tensor = torch.tensor(
    [
        [1, 2],
        [3, 4],
    ]
)

print("\nTensor:")

print(tensor)