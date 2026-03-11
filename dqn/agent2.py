import torch
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import csv
import os
import sys
sys.path.append("/home/pi/workspace/project/real/test")
from dqn.model import DQN
from dqn.memory import ReplayMemory
import random

class Agent:
    def __init__(self, state_dim, action_dim, device):
        self.device = device
        self.policy_net = DQN(state_dim, action_dim).to(device)
        self.policy_net.eval()
        self.target_net = DQN(state_dim, action_dim).to(device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.memory = ReplayMemory(10000)
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=1e-3)
        self.batch_size = 64
        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_decay = 0.9995  
        self.epsilon_min = 0.05
        self.action_dim = action_dim
        self.steps_done = 0
        self.target_update_freq = 30 

        self.prev_action = 0 #None
        
    def log_sensor_data(self, state):
        df = pd.DataFrame({'battery_percent': [state[0] * 100], 'timestamp': [time.time()]})
        df.to_csv("sensor_data_log.csv", mode='a', header=False, index=False)
    
    def select_action(self, state):
        battery_percent = state[0] * 100 

        if battery_percent < 30:
                action = 1
        elif battery_percent > 85:      #85
                action = 0
        else:
                if random.uniform(0, 1) < self.epsilon:
                        action = random.choice([0, 1])  
                else:
                        state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0).to(self.device)
                        with torch.no_grad():
                                action = self.policy_net(state_tensor).argmax().item()

        self.prev_action = action
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.epsilon_min)
        print(f"[DEBUG] Selected Action: {action}")  
        return action


    def optimize(self):
        if len(self.memory) < self.batch_size:
            return
        transitions = self.memory.sample(self.batch_size)
        batch = list(zip(*transitions))

        states = torch.tensor(np.array(batch[0]), dtype=torch.float32).to(self.device)
        actions = torch.tensor(batch[1]).unsqueeze(1).to(self.device)
        rewards = torch.tensor(batch[2], dtype=torch.float32).unsqueeze(1).to(self.device)
        next_states = torch.tensor(np.array(batch[3]), dtype=torch.float32).to(self.device)
        dones = torch.tensor(batch[4], dtype=torch.float32).unsqueeze(1).to(self.device)

        q_values = self.policy_net(states).gather(1, actions)
        next_q_values = self.target_net(next_states).max(1)[0].detach().unsqueeze(1)
        expected_q_values = rewards + (self.gamma * next_q_values * (1 - dones))

        loss = F.mse_loss(q_values, expected_q_values)

        self.optimizer.zero_grad()
        loss.backward()
        self.log_training_step(
                step=self.steps_done,
                loss=loss.item(),
                epsilon=self.epsilon,
                reward=rewards.mean().item(),
                action=actions[0].item()
        )
        self.optimizer.step()
        
        print(f"[TRAIN] Step: {self.steps_done}, Loss: {loss.item():.4f}, Epsilon: {self.epsilon:.4f}")#
        
        self.steps_done += 1
        if self.steps_done % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
    
    def load_model(self, path="dqn_model.pth"):#
        if os.path.exists(path):
                self.policy_net.load_state_dict(torch.load(path, map_location=self.device))
                self.policy_net.eval()
                self.target_net.load_state_dict(self.policy_net.state_dict())
                print(f"[MODEL] Loaded model from {path}")
        else:
                print(f"[MODEL] No model file found at {path}. Starting from scratch.")
    
    def save_model(self, path="dqn_model.pth"):#
        torch.save(self.policy_net.state_dict(), path)
        print(f"[MODEL] Saved model to {path}")

    def log_training_step(self, step, loss, epsilon, reward, action, log_path="train_log.csv"):
        log_exists = os.path.exists(log_path)
        with open(log_path, "a", newline="") as csvfile:
                writer = csv.writer(csvfile)
                if not log_exists:
                        writer.writerow(["Step", "Loss", "Epsilon", "Reward", "Action"])
                writer.writerow([step, loss, epsilon, reward, action])
