import torch

from src.segmentation.unet import UNet


def main():

    # Model
    model = UNet()

    # Loss Function
    criterion = torch.nn.BCEWithLogitsLoss()

    # Optimizer
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=0.001,
    )

    # Fake CT Image
    image = torch.randn(
        1,
        1,
        128,
        128,
    )

    # Fake Ground Truth Mask
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

    # Forward Pass
    prediction = model(image)

    # Compute Loss
    loss = criterion(
        prediction,
        target,
    )

    # Clear Previous Gradients
    optimizer.zero_grad()

    # Backpropagation
    loss.backward()

    # Update Weights
    optimizer.step()

    print(f"Loss: {loss.item():.4f}")
    print("One training step completed successfully!")


if __name__ == "__main__":
    main()