import torch
import torch.nn as nn
import torch.nn.functional as F

class DQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_dim, 256)  # Increased neurons for deeper learning
        self.bn1 = nn.BatchNorm1d(256)  # Batch Normalization for stable training
        self.fc2 = nn.Linear(256, 128)
        self.bn2 = nn.BatchNorm1d(128)
        self.fc3 = nn.Linear(128, 128)  # Added extra layer for finer adjustments
        self.out = nn.Linear(128, output_dim)
        self.dropout = nn.Dropout(0.3)  # Dropout to prevent overfitting

    def forward(self, x):
        x = F.relu(self.bn1(self.fc1(x)))
        x = self.dropout(F.relu(self.bn2(self.fc2(x))))
        x = F.relu(self.fc3(x))
        #return torch.sigmoid(self.out(x))  # Activation for smoother output
        return self.out(x)
