import torch
import torch.nn as nn

from src.segmentation.encoder import Encoder
from src.segmentation.bottleneck import Bottleneck
from src.segmentation.decoder_block import DecoderBlock


class UNet(nn.Module):
    """
    Complete U-Net Architecture.
    """

    def __init__(self):
        super().__init__()

        # Encoder
        self.encoder = Encoder()

        # Bottleneck
        self.bottleneck = Bottleneck()

        # Decoder
        self.decoder4 = DecoderBlock(1024, 512)
        self.decoder3 = DecoderBlock(512, 256)
        self.decoder2 = DecoderBlock(256, 128)
        self.decoder1 = DecoderBlock(128, 64)

        # Final Output Layer
        self.final_conv = nn.Conv2d(
            in_channels=64,
            out_channels=1,
            kernel_size=1,
        )

    def forward(self, x):

        # Encoder
        skips, x = self.encoder(x)

        # Bottleneck
        x = self.bottleneck(x)

        # Decoder
        x = self.decoder4(x, skips[3])
        x = self.decoder3(x, skips[2])
        x = self.decoder2(x, skips[1])
        x = self.decoder1(x, skips[0])

        # Final Prediction
        x = self.final_conv(x)

        return x


def main():

    model = UNet()

    sample = torch.randn(
        1,
        1,
        128,
        128,
    )

    output = model(sample)

    print(model)

    print("\nInput Shape :", sample.shape)
    print("Output Shape:", output.shape)


if __name__ == "__main__":
    main()