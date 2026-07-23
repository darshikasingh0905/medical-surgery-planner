import torch
import torch.nn as nn


class FirstConvolution(nn.Module):
    """
    Simple convolution layer example.
    """

    def __init__(self):
        super().__init__()

        self.conv = nn.Conv2d(
            in_channels=1,
            out_channels=8,
            kernel_size=3,
        )

    def forward(self, x):

        return self.conv(x)


def main():

    model = FirstConvolution()

    print(model)

    sample = torch.randn(
        1,   # Batch size
        1,   # Channels (Grayscale)
        128, # Height
        128, # Width
    )

    output = model(sample)

    print("\nInput Shape :", sample.shape)
    print("Output Shape:", output.shape)


if __name__ == "__main__":
    main()