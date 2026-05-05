#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import RPi.GPIO as gpio
from tempSensor import BMP180
from Temp_led import TemperatureLEDController
from PIRControl import PIRSensor

class TemperatureGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("온도 센서 & LED 제어 시스템")
        self.root.geometry("600x550")
        self.root.resizable(False, False)
        
        # 하드웨어 객체 초기화
        self.sensor = None
        self.led_controller = None
        self.pir_sensor = None
        
        # 상태 변수
        self.monitoring = False
        self.monitor_thread = None
        self.previous_threshold = 25.0
        
        self._create_widgets()
        
    def _create_widgets(self):
        """GUI 구성 요소 생성"""
        # 타이틀
        title_label = ttk.Label(self.root, text="온도 모니터링 시스템", font=("Arial", 18, "bold"))
        title_label.pack(pady=15)
        
        # 시스템 상태 프레임
        status_frame = ttk.LabelFrame(self.root, text="실시간 상태", padding=10)
        status_frame.pack(padx=15, pady=5, fill="both")
        
        # 온도 표시
        temp_container = ttk.Frame(status_frame)
        temp_container.pack(fill="x", pady=5)
        ttk.Label(temp_container, text="현재 온도:", font=("Arial", 12)).pack(side="left")
        self.temp_label = ttk.Label(temp_container, text="-- °C", font=("Arial", 16, "bold"), foreground="blue")
        self.temp_label.pack(side="left", padx=10)
        
        # LED(GPIO) 상태 표시
        gpio_frame = ttk.Frame(status_frame)
        gpio_frame.pack(fill="x", pady=5)
        self.labels = {}
        for key, text in [("low", "COLD (17)"), ("high", "HOT (4)"), ("mid", "COMFORT (27)")]:
            lbl = ttk.Label(gpio_frame, text=f"{text}: OFF", font=("Arial", 10), width=18)
            lbl.pack(side="left", padx=5)
            self.labels[key] = lbl

        # PIR 상태
        pir_frame = ttk.Frame(status_frame)
        pir_frame.pack(fill="x", pady=5)
        ttk.Label(pir_frame, text="보안 알림:", font=("Arial", 12)).pack(side="left")
        self.motion_label = ttk.Label(pir_frame, text="비활성", font=("Arial", 12, "bold"))
        self.motion_label.pack(side="left", padx=10)
        
        # 설정 프레임
        setting_frame = ttk.LabelFrame(self.root, text="제어 설정", padding=10)
        setting_frame.pack(padx=15, pady=10, fill="both")
        
        slider_frame = ttk.Frame(setting_frame)
        slider_frame.pack(fill="x")
        ttk.Label(slider_frame, text="임계 온도 설정:").pack(side="left")
        
        self.threshold_var = tk.DoubleVar(value=25.0)
        self.threshold_scale = ttk.Scale(slider_frame, from_=10, to=40, variable=self.threshold_var, 
                                         orient="horizontal", command=self._on_threshold_change)
        self.threshold_scale.pack(side="left", fill="x", expand=True, padx=10)
        
        self.threshold_display = ttk.Label(slider_frame, text="25.0°C", font=("Arial", 10, "bold"))
        self.threshold_display.pack(side="left")

        # 버튼 영역
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="시작", command=self._start_monitoring)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="중지", command=self._stop_monitoring, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        self.pir_btn = ttk.Button(btn_frame, text="PIR 켜기", command=self._toggle_pir)
        self.pir_btn.pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="종료", command=self._quit).pack(side="left", padx=5)
        
        # 로그 창
        log_frame = ttk.LabelFrame(self.root, text="시스템 로그")
        log_frame.pack(padx=15, pady=5, fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=6, font=("Courier", 9))
        self.log_text.pack(side="left", fill="both", expand=True)
        scroller = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroller.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scroller.set)

    def _log(self, message):
        """스레드 세이프한 로그 출력 (단순 업데이트는 root.update 대신 schedule 방식 권장하나 여기선 간단히 유지)"""
        timestamp = time.strftime("[%H:%M:%S] ")
        self.log_text.insert("end", timestamp + message + "\n")
        self.log_text.see("end")

    def _on_threshold_change(self, value):
        val = float(value)
        self.threshold_display.config(text=f"{val:.1f}°C")
        if self.led_controller:
            if val > self.previous_threshold:
                self.led_controller.signal_adjust_increase()
            elif val < self.previous_threshold:
                self.led_controller.signal_adjust_decrease()
            self.led_controller.set_threshold(val)
            self.previous_threshold = val

    def _start_monitoring(self):
        self.monitoring = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.threshold_scale.config(state="disabled")
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self._log("시스템 모니터링을 시작합니다.")

    def _monitor_loop(self):
        """메인 모니터링 로직"""
        try:
            # 하드웨어 초기화
            if not self.sensor:
                self.sensor = BMP180(bus_number=1, address=0x77)
            
            if not self.led_controller:
                self.led_controller = TemperatureLEDController(
                    self.sensor, gpio_pin_low_temp=17, gpio_pin_high_temp=4,
                    gpio_pin_comfortable=27, threshold_temp=self.threshold_var.get()
                )

            while self.monitoring:
                temp = self.led_controller.update()
                if temp is not None:
                    # GUI 업데이트 (메인 스레드에서 실행되도록 schedule)
                    self.root.after(0, self._update_ui, temp)
                time.sleep(2)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("오류", f"HW 제어 중 오류 발생: {e}"))
            self._stop_monitoring()
        finally:
            self._log("센서 루프 종료")

    def _update_ui(self, temp):
        """GUI 상태 업데이트 전용 함수"""
        self.temp_label.config(text=f"{temp:.2f} °C")
        status = self.led_controller.get_status()
        
        states = {
            "low": ("ON" if status['led_low_state'] else "OFF", "blue"),
            "high": ("ON" if status['led_high_state'] else "OFF", "red"),
            "mid": ("ON" if status['led_comfortable_state'] else "OFF", "green")
        }
        
        self.labels["low"].config(text=f"COLD: {states['low'][0]}", foreground=states['low'][1] if states['low'][0]=="ON" else "black")
        self.labels["high"].config(text=f"HOT: {states['high'][0]}", foreground=states['high'][1] if states['high'][0]=="ON" else "black")
        self.labels["mid"].config(text=f"COMFORT: {states['mid'][0]}", foreground=states['mid'][1] if states['mid'][0]=="ON" else "black")

    def _stop_monitoring(self):
        self.monitoring = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.threshold_scale.config(state="normal")
        self._log("모니터링이 중지되었습니다.")

    def _toggle_pir(self):
        if self.pir_sensor and self.pir_sensor.monitoring:
            self.pir_sensor.stop_monitoring()
            self.pir_btn.config(text="PIR 켜기")
            self.motion_label.config(text="비활성", foreground="black")
            self._log("PIR 센서를 껐습니다.")
        else:
            try:
                self.pir_sensor = PIRSensor(pir_pin=22, callback=self._pir_callback)
                self.pir_sensor.start_monitoring()
                self.pir_btn.config(text="PIR 끄기")
                self.motion_label.config(text="감시 중...", foreground="green")
                self._log("PIR 보안 모드 가동 중...")
            except Exception as e:
                messagebox.showerror("PIR 오류", str(e))

    def _pir_callback(self, motion_detected):
        if motion_detected:
            self.root.after(0, lambda: self.motion_label.config(text="움직임 감지!", foreground="red"))
            self.root.after(0, lambda: self._log("경고: 움직임이 감지되었습니다!"))
        else:
            self.root.after(0, lambda: self.motion_label.config(text="감시 중...", foreground="green"))

    def _quit(self):
        if self.monitoring:
            if not messagebox.askyesno("확인", "모니터링이 실행 중입니다. 정말 종료할까요?"):
                return
        
        self.monitoring = False
        if self.pir_sensor:
            self.pir_sensor.stop_monitoring()
        
        gpio.cleanup()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TemperatureGUI(root)
    root.mainloop()