import torch

from src.segmentation.unet import UNet


def main():

    model = UNet()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=0.001,
    )

    print(model)

    print("\nOptimizer:")
    print(optimizer)


if __name__ == "__main__":
    main()