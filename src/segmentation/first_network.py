import torch
import torch.nn as nn


class FirstNeuralNetwork(nn.Module):
    """
    A simple fully connected neural network.
    """

    def __init__(self):
        super().__init__()

        self.fc1 = nn.Linear(4, 8)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(8, 2)

    def forward(self, x):

        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)

        return x


def main():

    model = FirstNeuralNetwork()

    print(model)

    sample = torch.randn(1, 4)

    output = model(sample)

    print("\nInput Shape :", sample.shape)
    print("Output Shape:", output.shape)
    print("\nPrediction:")

    print(output)


if __name__ == "__main__":
    main()