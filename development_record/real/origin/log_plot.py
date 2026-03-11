import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("train_log.csv")

df = df.sort_values("Step")

#plt.style.use("seaborn-vibrant")
plt.style.use("ggplot")

# 1. Loss
plt.figure(figsize=(10, 4))
plt.plot(df["Step"], df["Loss"], label="Loss", color="red")
plt.xlabel("Step")
plt.ylabel("Loss")
plt.title("Training Loss over Time")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("loss_plot.png")
#plt.show()

# 2. Epsilon
plt.figure(figsize=(10, 4))
plt.plot(df["Step"], df["Epsilon"], label="Epsilon", color="blue")
plt.xlabel("Step")
plt.ylabel("Epsilon")
plt.title("Epsilon Decay")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("epsilon_plot.png")
#plt.show()

# 3. Reward
plt.figure(figsize=(10, 4))
plt.plot(df["Step"], df["Reward"], label="Reward", color="green")
plt.xlabel("Step")
plt.ylabel("Reward")
plt.title("Reward over Time")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("reward_plot.png")
#plt.show()
