import torch
import torch.nn as nn

from src.segmentation.cnn_block import CNNBlock


class Bottleneck(nn.Module):
    """
    U-Net Bottleneck.
    """

    def __init__(self):
        super().__init__()

        self.block = CNNBlock(
            in_channels=512,
            out_channels=1024,
        )

    def forward(self, x):

        return self.block(x)


def main():

    bottleneck = Bottleneck()

    sample = torch.randn(
        1,
        512,
        8,
        8,
    )

    output = bottleneck(sample)

    print("Input Shape :", sample.shape)
    print("Output Shape:", output.shape)


if __name__ == "__main__":
    main()