import torch
import torch.nn as nn

from src.segmentation.cnn_block import CNNBlock


class DecoderBlock(nn.Module):
    """
    U-Net Decoder Block.

    Upsampling
        ↓
    CNN Block
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
    ):
        super().__init__()

        self.up = nn.ConvTranspose2d(
            in_channels,
            out_channels,
            kernel_size=2,
            stride=2,
        )

        self.conv = CNNBlock(
            in_channels=out_channels,
            out_channels=out_channels,
        )

    def forward(self, x):

        x = self.up(x)

        x = self.conv(x)

        return x


def main():

    decoder = DecoderBlock(
        in_channels=1024,
        out_channels=512,
    )

    sample = torch.randn(
        1,
        1024,
        8,
        8,
    )

    output = decoder(sample)

    print("Input Shape :", sample.shape)
    print("Output Shape:", output.shape)


if __name__ == "__main__":
    main()