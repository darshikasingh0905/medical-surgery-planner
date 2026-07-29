import torch
import torch.nn as nn


def main():

    loss_function = nn.BCEWithLogitsLoss()

    prediction = torch.randn(
        1,
        1,
        128,
        128,
    )

    target = torch.randint(
        0,
        2,
        (
            1,
            1,
            128,
            128,
        ),
    ).float()

    loss = loss_function(
        prediction,
        target,
    )

    print("Prediction Shape:", prediction.shape)
    print("Target Shape    :", target.shape)
    print("Loss            :", loss.item())


if __name__ == "__main__":
    main()