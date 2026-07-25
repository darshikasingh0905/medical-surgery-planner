import torch
import torch.nn as nn

from src.segmentation.cnn_block import CNNBlock


class EncoderBlock(nn.Module):
    """
    U-Net Encoder Block.

    CNN Block
        ↓
    Max Pooling
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
    ):
        super().__init__()

        self.conv = CNNBlock(
            in_channels,
            out_channels,
        )

        self.pool = nn.MaxPool2d(
            kernel_size=2,
            stride=2,
        )

    def forward(self, x):

        features = self.conv(x)

        pooled = self.pool(features)

        return features, pooled


def main():

    encoder = EncoderBlock(
        in_channels=1,
        out_channels=64,
    )

    sample = torch.randn(
        1,
        1,
        128,
        128,
    )

    features, pooled = encoder(sample)

    print("Input Shape     :", sample.shape)
    print("Feature Shape   :", features.shape)
    print("Pooled Shape    :", pooled.shape)


if __name__ == "__main__":
    main()