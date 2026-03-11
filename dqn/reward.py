def calculate_reward(battery_percent, temperature, is_charging, prev_action):
    reward = 0.0

    # Encourage stable charging behavior
    if is_charging and battery_percent < 40:
        reward += 1.0  # Positive reward for charging when battery is low
    elif not is_charging and battery_percent > 80:      #80
        reward += 1.0  # Positive reward for stopping charge at high battery level
    elif 40 <= battery_percent <= 80:
        reward += 0.1 if is_charging else -0.1

    # Penalize frequent switching of charging state
    if prev_action is not None and prev_action != is_charging:
        reward -= 0.5  # Apply penalty if the state changes too frequently
        
    if prev_action is None:
        print("[WARN] prev_action is None - using default reward logic")

    # Penalize high temperature situations
    if temperature >= 45:
        reward -= 2.0  # Stronger penalty for overheating
    elif temperature < 10: # >=41
        reward -= 1.0
    print(f"[REWARD] SoC: {battery_percent:.1f}%, Temp: {temperature:.1f}C, "
          f"Action: {is_charging}, Prev: {prev_action}, Reward: {reward:.2f}")
          
    return reward
