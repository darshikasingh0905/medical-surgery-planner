import torch

from src.segmentation.unet import UNet


def main():

    model = UNet()

    criterion = torch.nn.BCEWithLogitsLoss()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=0.001,
    )

    image = torch.randn(
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

    num_epochs = 5

    for epoch in range(num_epochs):

        optimizer.zero_grad()

        prediction = model(image)

        loss = criterion(
            prediction,
            target,
        )

        loss.backward()

        optimizer.step()

        print(
            f"Epoch {epoch + 1}/{num_epochs} | Loss: {loss.item():.4f}"
        )


if __name__ == "__main__":
    main()