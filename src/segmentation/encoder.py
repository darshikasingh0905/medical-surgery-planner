import torch
import torch.nn as nn

from src.segmentation.encoder_block import EncoderBlock


class Encoder(nn.Module):
    """
    U-Net Encoder.
    """

    def __init__(self):
        super().__init__()

        self.encoder1 = EncoderBlock(1, 64)
        self.encoder2 = EncoderBlock(64, 128)
        self.encoder3 = EncoderBlock(128, 256)
        self.encoder4 = EncoderBlock(256, 512)

    def forward(self, x):

        skip1, x = self.encoder1(x)
        skip2, x = self.encoder2(x)
        skip3, x = self.encoder3(x)
        skip4, x = self.encoder4(x)

        return [skip1, skip2, skip3, skip4], x


def main():

    encoder = Encoder()

    sample = torch.randn(
        1,
        1,
        128,
        128,
    )

    skips, bottleneck_input = encoder(sample)

    print("Skip 1:", skips[0].shape)
    print("Skip 2:", skips[1].shape)
    print("Skip 3:", skips[2].shape)
    print("Skip 4:", skips[3].shape)
    print("Bottleneck Input:", bottleneck_input.shape)


if __name__ == "__main__":
    main()