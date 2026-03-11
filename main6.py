import os
import time
import threading
import tkinter as tk
import customtkinter as ctk
import RPi.GPIO as GPIO
from sensor_module import read_sensor_data, get_sensor_data, update_battery_percentage
import board
import busio
import digitalio
import adafruit_ssd1306
import sqlite3
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont
import torch
from dqn.agent import Agent
from dqn.reward import calculate_reward


#RELAY_IN1 = 21
#RELAY_IN2 = 20

#GPIO.setmode(GPIO.BCM)
#GPIO.setup(RELAY_IN1, GPIO.OUT)
#GPIO.setup(RELAY_IN2, GPIO.OUT)
#GPIO.output(RELAY_IN1, GPIO.HIGH)
#GPIO.output(RELAY_IN2, GPIO.HIGH)

# Initialize relay pins
relay1 = digitalio.DigitalInOut(board.D21)
relay1.direction = digitalio.Direction.OUTPUT
relay2 = digitalio.DigitalInOut(board.D20)
relay2.direction = digitalio.Direction.OUTPUT

relay1.value = False
relay2.value = False

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
agent = Agent(state_dim=2, action_dim=2, device=device)

def start_charging():
    relay1.value = True
    relay2.value = True
    #GPIO.output(RELAY_IN1, GPIO.LOW)
    #GPIO.output(RELAY_IN2, GPIO.HIGH)
    print("Charge start!")

def stop_charging():
    relay1.value = True
    relay2.value = False
    #GPIO.output(RELAY_IN1, GPIO.LOW)
    #GPIO.output(RELAY_IN2, GPIO.LOW)
    print("Charge stop!")

def cleanup():
    relay1.value = False
    relay2.value = False
    #GPIO.output(RELAY_IN1, GPIO.HIGH)
    #GPIO.output(RELAY_IN2, GPIO.HIGH)
    GPIO.cleanup()
    print("GPIO cleanup complete")


#spi
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)

dc = digitalio.DigitalInOut(board.D27)
reset = digitalio.DigitalInOut(board.D22)
cs = digitalio.DigitalInOut(board.CE0)
WIDTH = 128
HEIGHT = 64
display = adafruit_ssd1306.SSD1306_SPI(WIDTH, HEIGHT, spi, dc, reset, cs) #spi

#i2c
i2c = busio.I2C(board.SCL, board.SDA)
reset_pin = digitalio.DigitalInOut(board.D4)
reset_pin.direction = digitalio.Direction.OUTPUT


#display = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C, reset=reset_pin) #i2c
display.fill(0)
display.show()

width = display.width
height = display.height
image = Image.new("1", (width, height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()
font1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/FreeSans.ttf", size=13) ##

sensor_data = get_sensor_data()
manual_mode = False

def update_display():
    global sensor_data
    while True:
        try:
            voltage = sensor_data.get("volt", 0.0)
            current = sensor_data.get("curr", 0.0)
            temperature = sensor_data.get("temp", 0.0)
            percent = sensor_data.get("percent", 0)
            health = sensor_data.get("health", 0)
            bar_length = int((percent / 100) * 60)
            bar_length2 = int((health / 100) * 60) ##

            draw.rectangle((0, 0, width, height), fill=0)
            draw.text((0, 0), f"Voltage: {voltage:.2f} V", font=font1, fill=255)
            draw.text((0, 12), f"Current: {current:.3f} mA", font=font1, fill=255)
            draw.text((0, 24), f"Temp: {temperature:.1f} C", font=font1, fill=255)
            draw.text((0, 36), f"SoC: {percent:.0f}%", font=font1, fill=255)
            draw.text((0, 48), f"SoH: {health:.0f}%", font=font1, fill=255) ##
            
            draw.rectangle((65, 41, 125, 46), outline=255, fill=0) ##
            draw.rectangle((65, 41, 65 + bar_length, 46), fill=255) ##
            draw.rectangle((65, 53, 125, 58), outline=255, fill=0) ##
            draw.rectangle((65, 53, 65 + bar_length2, 58), fill=255) ##

            display.image(image)
            display.show()

            time.sleep(1)
        except Exception as e:
            print("OLED update error:", e)
            time.sleep(1)
            
class LoginFrame(tk.Frame):
    def __init__(self, parent, switch_to_monitor):
        super().__init__(parent, bg="#f5f5f5")
        self.switch_to_monitor = switch_to_monitor

        tk.Label(self, text="Device Login", font=("Helvetica", 18, "bold"),
                 bg="#f5f5f5", fg="#2e3b4e").pack(pady=(100, 10))

        tk.Label(self, text="Enter device name", font=("Helvetica", 12),
                 bg="#f5f5f5", fg="#607d8b").pack(pady=(0, 30))

        self.entry = tk.Entry(self, font=("Helvetica", 14), justify="center")
        self.entry.pack(pady=20, ipadx=10, ipady=5)

        access_button = ctk.CTkButton(
            self,
            text="Access",
            command=self.on_submit,
            font=("Helvetica", 15),
            #corner_radius=10,       
            fg_color="#2748ED",     
            text_color="#f5f5f5",     
            hover_color="#2a5db0"    
        )
        access_button.pack(pady=10)



    def on_submit(self):
        device_name = self.entry.get().strip()
        if not device_name:
            tk.messagebox.showwarning("error", "Please enter a device name.")
            return

        conn = sqlite3.connect("devices.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices WHERE name = ?", (device_name,))
        result = cursor.fetchone()
        conn.close()

        if result:
            self.switch_to_monitor()
        else:
            tk.messagebox.showerror("error", "Device not registered.")


class BatteryMonitorApp(tk.Frame):
    def __init__(self):
        super().__init__(bg="#f5f5f5")

        tk.Label(self, text="Battery Monitor", font=("Helvetica", 18, "bold"), bg="#f5f5f5", fg="#2e3b4e").pack(pady=(40,10))
        self.create_battery_circle()
        
        info_box = ctk.CTkFrame(self, fg_color="white")
        info_box.pack(padx=20, pady=20, fill="x")
        info_box.pack_propagate(False)
        info_box.grid_rowconfigure(0, minsize=50)
        info_box.grid_columnconfigure(0, weight=0)
        info_box.grid_columnconfigure(2, weight=0)
        info_box.grid_columnconfigure(4, weight=0)
        # Temp
        tk.Label(info_box, text="Temp", font=("Helvetica", 10), bg="white", fg="#999").grid(row=0, column=0, padx=(10, 2), sticky="w")
        self.label_temp = tk.Label(info_box, text="--C", font=("Helvetica", 10, "bold"), bg="white", fg="#2e3b4e")
        self.label_temp.grid(row=0, column=1, padx=(0, 10), sticky="w")

        # Volt
        tk.Label(info_box, text="Volt", font=("Helvetica", 10), bg="white", fg="#999").grid(row=0, column=2, padx=(40, 2), sticky="w")
        self.label_voltage = tk.Label(info_box, text="--V", font=("Helvetica", 10, "bold"), bg="white", fg="#2e3b4e")
        self.label_voltage.grid(row=0, column=3, padx=(0, 10), sticky="w")

        # Curr
        tk.Label(info_box, text="Curr", font=("Helvetica", 10), bg="white", fg="#999").grid(row=0, column=4, padx=(40, 2), sticky="w")
        self.label_current = tk.Label(info_box, text="--A", font=("Helvetica", 10, "bold"), bg="white", fg="#2e3b4e")
        self.label_current.grid(row=0, column=5, padx=(0, 10), sticky="e")
        ###########
        
        # Battery Health & Charging Status - Separate Boxes
        status_box = tk.Frame(self, bg="#f5f5f5")
        status_box.pack(padx=20, pady=(0, 20), fill="x")
    
        # Battery Health Box
        health_frame = tk.Frame(status_box, bg="white", width=170, height=90)
        health_frame.pack(side="left", padx=(0, 5))
        health_frame.pack_propagate(False)
        tk.Label(health_frame, text="Battery Health", font=("Helvetica", 10), bg="white", fg="#999").pack(anchor="w", padx=10, pady=(10, 20))
        self.label_health = tk.Label(health_frame, text="--%", font=("Helvetica", 13, "bold"), bg="white", fg="#333333")
        self.label_health.pack(anchor="w", padx=10, pady=(0, 12))

        # Charging Status Box
        charge_frame = tk.Frame(status_box, bg="white", width=170, height=90)
        charge_frame.pack(side="right", padx=(5, 0))
        charge_frame.pack_propagate(False)
        tk.Label(charge_frame, text="Charging Status", font=("Helvetica", 10), bg="white", fg="#999").pack(anchor="w", padx=10, pady=(10, 20))
        self.label_status = tk.Label(charge_frame, text="Not Charging", font=("Helvetica", 13, "bold"), bg="white", fg="#333333")
        self.label_status.pack(anchor="w", padx=10,pady=(0, 12))

        # Notice Box
        notice_box = tk.Frame(self, bg="white", height=80)
        notice_box.pack(padx=20, pady=(0, 10), fill="x")
        notice_box.pack_propagate(False)
        tk.Label(notice_box, text="Notice", font=("Helvetica", 10), bg="white", fg="#999").pack(anchor="w", padx=10, pady=10)
        self.label_notice = tk.Label(notice_box, text="", font=("Helvetica", 11), bg="white", fg="#DC3336", justify="left", anchor="nw")
        self.label_notice.pack(fill="both", expand=True, padx=10, pady=8)
    
        # Frame top: menu switch + start charging button (위쪽)
        frame_top = tk.Frame(self, bg="#f5f5f5")
        frame_top.pack(pady=(10,10), fill="x")

        self.manual_mode_switch = ctk.CTkSwitch(
            frame_top,
            text="Manual Mode",
            font=("Helvetica", 15, "normal"),
            command=self.toggle_manual_mode,
            progress_color="#2748ED",
            button_color="#D7D7D7",
            button_hover_color="#B7B7B7",
            fg_color="#9B9B9B"
        )
        self.manual_mode_switch.pack(side="left", padx=(20,0), pady=(10,0))

        self.toggle_button = ctk.CTkButton(
            frame_top,
            text="Start Charging",
            font=("Helvetica", 15),
            fg_color="#2748ED",
            text_color="white",
            hover_color="#2a5db0",
            #corner_radius=10,
            #width=140,
            #height=30,
            command=self.toggle_charging
        )
        self.toggle_button.pack(side="right", padx=(5, 20))
        self.toggle_button.pack_forget()
        
        # Bottom Frame for Switch + Start Charging Button
        bottom_frame = tk.Frame(self, bg="#f5f5f5")
        bottom_frame.pack(side="bottom", pady=(20,10), fill="x")

        self.entry_temp = tk.Entry(bottom_frame, width=4)
        self.entry_temp.insert(0, "25")
        self.entry_temp.pack(side="left")
        tk.Label(bottom_frame, text=" C", bg="#f5f5f5").pack(side="left", padx=(2, 10))

        self.entry_voltage = tk.Entry(bottom_frame, width=4)
        self.entry_voltage.insert(0, "3.7")
        self.entry_voltage.pack(side="left")
        tk.Label(bottom_frame, text=" V", bg="#f5f5f5").pack(side="left", padx=(2, 10))

        self.entry_current = tk.Entry(bottom_frame, width=4)
        self.entry_current.insert(0, "1.2")
        self.entry_current.pack(side="left")
        tk.Label(bottom_frame, text=" A", bg="#f5f5f5").pack(side="left", padx=(2, 10))

        tk.Button(bottom_frame, text="Update", command=self.set_manual_data,
                  bg="#6D6D6D", fg="white", font=("Helvetica", 10)).pack(side="left", padx=10)
        
        self.backup_sensor_data = None 
        self.update_battery_info()        
              
    def update_charging_status(self, is_charging):
        status_text = "Charging" if is_charging else "Not Charging"
        status_color = "#2748ED" if is_charging else "#333333"
        arc_color = "#2748ED" if is_charging else "#94A3EC"
        self.label_status.config(text=status_text, fg=status_color)
        self.circle_canvas.itemconfig(self.circle_arc, outline=arc_color)
    
    def toggle_charging(self):
        start_charging()
        self.update_charging_status(True)
        
        
    def create_battery_circle(self):
        self.circle_canvas = tk.Canvas(self, width=180, height=180, bg="#f5f5f5", highlightthickness=0)
        self.circle_canvas.pack(pady=(20, 10))
        self.circle_bg = self.circle_canvas.create_oval(10, 10, 170, 170, outline="#E4E4E4", width=20)
        self.circle_arc = self.circle_canvas.create_arc(10, 10, 170, 170, start=90, extent=0, style="arc", outline="#2748ED", width=20)
        self.circle_text = self.circle_canvas.create_text(90, 90, text="--%", font=("Helvetica", 20, "bold"), fill="#2e3b4e")

    def toggle_manual_mode(self):
        global manual_mode
        if self.manual_mode_switch.get() == 1:
            manual_mode = True
            self.toggle_button.pack(side="right", padx=(5, 20))  # 버튼 보이게
            self.label_notice.config(text="Manual mode ON - Automatic control paused.")
        else:
            manual_mode = False
            self.toggle_button.pack_forget()  # 버튼 숨기기
            self.label_notice.config(text="Manual mode OFF - Automatic control resumed.")

            
    def toggle_charging(self):
        global manual_mode
        if not manual_mode:
            self.label_notice.config(text="Enable Manual Mode to control charging manually.")
            return

        current_text = self.toggle_button.cget("text")
        if current_text == "Start Charging":
            start_charging()
            self.update_charging_status(True)
            self.toggle_button.configure(
                text="Stop Charging",
                fg_color="#9B9B9B",  # Stop 버튼 색상 변경
                hover_color="#7B7B7B"  # hover 색상도 변경하면 자연스러움
            )
            self.label_notice.config(text="Charging started (manual).")
        else:
            stop_charging()
            self.update_charging_status(False)
            self.toggle_button.configure(
                text="Start Charging",
                fg_color="#2748ED",  # 다시 Start 버튼 색상으로
                hover_color="#2a5db0"
            )
            self.label_notice.config(text="Charging stopped (manual).")





    def set_manual_data(self):
        global manual_mode, sensor_data
        try:
            voltage = float(self.entry_voltage.get())
            current = float(self.entry_current.get())
            temp = float(self.entry_temp.get())

            self.backup_sensor_data = sensor_data.copy()


            sensor_data["volt"] = voltage
            sensor_data["curr"] = current
            sensor_data["temp"] = temp
            sensor_data["percent"] = sensor_data.get("percent", 0)


            manual_mode = True
            print("Manual mode ON - custom values set.")
            self.after(10000, self.reset_sensor_mode) 
        except ValueError:
            print("Invalid input. Please enter numeric values.")
            
        if temp >= 41:
            stop_charging()
            self.update_charging_status(False)
            self.label_notice.config(text="High temperature! Charging stopped..")
            self.after(10000, lambda: self.label_notice.config(text=""))
        elif voltage >= 4.26:
            stop_charging()
            self.update_charging_status(False)
            self.label_notice.config(text="High voltage! Charging stopped..")
            self.after(10000, lambda: self.label_notice.config(text=""))
        elif current >= 3.5:
            stop_charging()
            self.update_charging_status(False)
            self.label_notice.config(text="High current! Charging stopped..")
            self.after(10000, lambda: self.label_notice.config(text=""))
        else:
            start_charging()
            self.update_charging_status(True)


    def reset_sensor_mode(self):
        global manual_mode, sensor_data
        manual_mode = False
        if self.backup_sensor_data:
            sensor_data.update(self.backup_sensor_data)
            print("Manual mode OFF - restored sensor data.")
        else:
            print("Manual mode OFF - no backup data found.")


    def update_battery_info(self):
        voltage = sensor_data.get("volt", 0.0)
        current = sensor_data.get("curr", 0.0)
        temp = sensor_data.get("temp", 0.0)
        percent = sensor_data.get("percent", 0)
        health = sensor_data.get("health", 0)
        
        self.label_voltage.config(text=f"{voltage:.2f} V")
        self.label_current.config(text=f"{current:.2f} mA")
        self.label_temp.config(text=f"{temp:.1f} C")
        self.label_health.config(text=f"{health:.0f}%")
        
        angle = int(percent * 3.6) 
        self.circle_canvas.itemconfig(self.circle_arc, extent=-angle)
        self.circle_canvas.itemconfig(self.circle_text, text=f"{percent}%")

        self.after(1000, self.update_battery_info)

def sensor_loop():
    global manual_mode, sensor_data, app
    prev_percent = sensor_data.get("percent", 0)
    
    while True:
        if manual_mode:
            time.sleep(1)
            continue
            
        sensor_data = read_sensor_data()
        """
         if not manual_mode:
            sensor_data = read_sensor_data()
        """
        voltage = sensor_data.get("volt", 0.0)
        battery_percent = update_battery_percentage(voltage, prev_percent)
        sensor_data["percent"] = battery_percent 
        print(f"[DEBUG] Updated Sensor Data: {sensor_data}")
        
        #battery_percent = sensor_data.get("percent", 0) / 100.0
        temperature = sensor_data.get("temp", 25.0)
        #state = [battery_percent, temperature / 50.0]
        state = [battery_percent / 100.0, temperature / 50.0]

        action = agent.select_action(state)
        
        if not manual_mode:
            if action == 1:
                start_charging()
                app.label_status.after(0, lambda: app.update_charging_status(True))
            else:
                stop_charging()
                app.label_status.after(0, lambda: app.update_charging_status(False))

        
        prev_percent = battery_percent
        reward = calculate_reward(battery_percent, temperature, action, agent.prev_action)
        next_state = [sensor_data.get("percent", 0) / 100.0, sensor_data.get("temp", 25.0) / 50.0]
        agent.memory.push(state, action, reward, next_state, False)
        agent.optimize()

        time.sleep(1)

def monitor_usb_connection():
    global app, manual_mode
    usb_connected = False

    while True:
        is_connected = os.path.exists('/dev/ttyUSB0')
        if is_connected != usb_connected:
            usb_connected = is_connected

            if usb_connected:
                print("CP2102 USB connected. Starting charging.")
                app.label_notice.after(0, lambda: app.label_notice.config(text="USB connected. Charging enabled.",fg="#333333"))
                manual_mode = False
            else:
                print("CP2102 USB disconnected. Stopping charging.")
                app.label_notice.after(0, lambda: app.label_notice.config(text="USB disconnected. Charging disabled.",fg="#333333"))
                stop_charging()
                app.label_status.after(0, lambda: app.update_charging_status(False))
                manual_mode = True 

        time.sleep(2)


def main():
    global app
    try:
        root = tk.Tk()
        root.title("Smart Battery Monitor")
        root.geometry("400x900")
        root.configure(bg="#f5f5f5")

        def show_monitor():
            global app
            login_frame.pack_forget()
            app = BatteryMonitorApp()
            app.pack(fill="both", expand=True)
            threading.Thread(target=sensor_loop, daemon=True).start()
            threading.Thread(target=update_display, daemon=True).start()
            threading.Thread(target=monitor_usb_connection, daemon=True).start()

        login_frame = LoginFrame(root, switch_to_monitor=show_monitor)
        login_frame.pack(fill="both", expand=True)

        root.mainloop()

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()



