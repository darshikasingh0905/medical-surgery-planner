import torch
import torch.nn as nn


class CNNBlock(nn.Module):
    """
    Basic CNN block used in U-Net.

    Conv → ReLU → Conv → ReLU
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
    ):
        super().__init__()

        self.block = nn.Sequential(

            nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                padding=1,
            ),

            nn.ReLU(inplace=True),

            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=3,
                padding=1,
            ),

            nn.ReLU(inplace=True),
        )

    def forward(self, x):

        return self.block(x)


def main():

    block = CNNBlock(
        in_channels=1,
        out_channels=64,
    )

    print(block)

    sample = torch.randn(
        1,
        1,
        128,
        128,
    )

    output = block(sample)

    print("\nInput Shape :", sample.shape)
    print("Output Shape:", output.shape)


if __name__ == "__main__":
    main()