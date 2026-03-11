import random
import numpy as np
from collections import deque

class ReplayMemory:
    def __init__(self, capacity):
        """Initialize Replay Memory with prioritization."""
        self.memory = deque(maxlen=capacity)
        self.priorities = deque(maxlen=capacity)  # Track experience priorities

    def push(self, state, action, reward, next_state, done):
        """Store experience with its priority."""
        experience = (state, action, reward, next_state, done)
        self.memory.append(experience)

        # Assign priority based on absolute reward (higher reward -> higher priority)
        priority = abs(reward) + 1e-5  # Small offset to prevent zero priority
        self.priorities.append(priority)

    def sample(self, batch_size):
        """Sample experiences based on priority."""
        if len(self.memory) < batch_size:
            return random.sample(self.memory, batch_size)

        # Normalize priorities for probability distribution
        priorities = np.array(self.priorities, dtype=np.float32)
        probabilities = priorities / priorities.sum()

        indices = np.random.choice(len(self.memory), batch_size, p=probabilities)
        return [self.memory[i] for i in indices]

    def __len__(self):
        return len(self.memory)
