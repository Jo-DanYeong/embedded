import RPi.GPIO as gpio
import time


class TemperatureLEDController:
    
    def __init__(self, sensor, gpio_pin_low_temp, gpio_pin_high_temp, gpio_pin_comfortable, threshold_temp=25.0):
        self.sensor = sensor
        self.led_low_temp = gpio_pin_low_temp
        self.led_high_temp = gpio_pin_high_temp
        self.led_comfortable = gpio_pin_comfortable
        self.threshold_temp = threshold_temp
        self.led_low_state = False
        self.led_high_state = False
        self.led_comfortable_state = False
        
        # GPIO 설정
        gpio.setmode(gpio.BCM)
        gpio.setup(self.led_low_temp, gpio.OUT)
        gpio.setup(self.led_high_temp, gpio.OUT)
        gpio.setup(self.led_comfortable, gpio.OUT)
    
    def update(self):
        """온도를 읽고 LED 상태를 업데이트"""
        try:
            current_temp = self.sensor.read_temperature()
            target_temp = self.threshold_temp
            self.led_controll(target_temp, current_temp)

            return current_temp
        except Exception as e:
            print(f"온도 읽기 오류: {e}")
            return None
    
    def led_controll(self, target_temp ,current_temp):
        temp_diff = abs(current_temp - self.threshold_temp)

        # 임계값 ±2°C 범위 체크
        if temp_diff <= 2.0:
            gpio.output(self.led_low_temp, gpio.LOW)
            gpio.output(self.led_high_temp, gpio.LOW)
            gpio.output(self.led_comfortable, gpio.HIGH)
            self.led_comfortable_state = True
            self.led_low_state = False
            self.led_high_state = False
            return
        
        gpio.output(self.led_comfortable, gpio.LOW)
        self.led_comfortable_state = False

        # GPIO 17: 낮은 온도 체크하고, 파란색 led켜기
        if current_temp < target_temp:
            gpio.output(self.led_low_temp, gpio.HIGH)
            gpio.output(self.led_high_temp, gpio.LOW)
            self.led_low_state = True
            self.led_high_state = False
            self.led_comfortable_state = False
            print(f"GPIO {self.led_low_temp} ON (낮은 온도: {current_temp:.2f}°C < {self.threshold_temp}°C)")
        else:
            # GPIO 4: 높은 온도 체크하고, 빨간색 led켜기
            gpio.output(self.led_high_temp, gpio.HIGH)
            gpio.output(self.led_low_temp, gpio.LOW)
            self.led_high_state = True
            self.led_low_state = False
            self.led_comfortable_state = False
            print(f"GPIO {self.led_high_temp} ON (높은 온도: {current_temp:.2f}°C >= {self.threshold_temp}°C)")
    
    def get_status(self):
        """
            dict: 'led_low_state', 'led_high_state', 'led_comfortable_state', 'threshold'
        """
        return {
            'led_low_state': self.led_low_state,
            'led_high_state': self.led_high_state,
            'led_comfortable_state': self.led_comfortable_state,
            'threshold': self.threshold_temp
        }
    
    def set_threshold(self, new_threshold):
        self.threshold_temp = new_threshold
        print(f"임계값 변경: {new_threshold}°C")
    
    def signal_adjust_increase(self):
        """임계값 증가 신호"""
        print(f"임계값 증가 신호 활성화")
    
    def signal_adjust_decrease(self):
        """임계값 감소 신호"""
        print(f"임계값 감소 신호 활성화")
    
    def close(self):
        """LED 끄고 GPIO 정리"""
        self.led_low_state = False
        self.led_high_state = False
        self.led_comfortable_state = False
        print(f"GPIO {self.led_low_temp} OFF")
        print(f"GPIO {self.led_high_temp} OFF")
        print(f"GPIO {self.led_comfortable} OFF")
        gpio.cleanup()
