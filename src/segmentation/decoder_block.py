import torch
import torch.nn as nn

from src.segmentation.cnn_block import CNNBlock


class DecoderBlock(nn.Module):
    """
    U-Net Decoder Block.

    Upsampling
        ↓
    Skip Connection
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
            in_channels=out_channels * 2,
            out_channels=out_channels,
        )

    def forward(
        self,
        x,
        skip,
    ):

        x = self.up(x)

        x = torch.cat(
            [x, skip],
            dim=1,
        )

        x = self.conv(x)

        return x


def main():

    decoder = DecoderBlock(
        in_channels=1024,
        out_channels=512,
    )

    bottleneck_output = torch.randn(
        1,
        1024,
        8,
        8,
    )

    skip_connection = torch.randn(
        1,
        512,
        16,
        16,
    )

    output = decoder(
        bottleneck_output,
        skip_connection,
    )

    print("Bottleneck Output :", bottleneck_output.shape)
    print("Skip Connection   :", skip_connection.shape)
    print("Decoder Output    :", output.shape)


if __name__ == "__main__":
    main()