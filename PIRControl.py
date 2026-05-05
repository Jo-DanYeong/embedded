import RPi.GPIO as gpio
import time
import threading


class PIRSensor:
    
    def __init__(self, pir_pin=22, callback=None):
        self.pir_pin = pir_pin
        self.callback = callback
        self.monitoring = False
        self.monitor_thread = None
        self.motion_detected = False
        
        # GPIO 설정
        gpio.setmode(gpio.BCM)
        gpio.setup(self.pir_pin, gpio.IN)
    
    def start_monitoring(self):
        """PIR 모니터링 시작"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """PIR 모니터링 중지"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        self.motion_detected = False
    
    def _monitor_loop(self):
        """PIR 모니터링 루프"""
        while self.monitoring:
            try:
                motion = gpio.input(self.pir_pin)
                
                if motion and not self.motion_detected:
                    # 모션이 감지되었을 때
                    self.motion_detected = True
                    if self.callback:
                        self.callback(True)
                
                elif not motion and self.motion_detected:
                    # 모션이 감지되지 않을 때
                    self.motion_detected = False
                    if self.callback:
                        self.callback(False)
                
                time.sleep(0.1)
            
            except Exception as e:
                print(f"PIR 모니터링 오류: {e}")
                break
    
    def is_motion_detected(self):
        """현재 모션 감지 상태 반환"""
        return self.motion_detected
    
    def get_status(self):
        """PIR 센서 상태 반환"""
        return {
            'pir_pin': self.pir_pin,
            'monitoring': self.monitoring,
            'motion_detected': self.motion_detected
        }
    
    def cleanup(self):
        """GPIO 정리"""
        self.stop_monitoring()
        try:
            gpio.cleanup(self.pir_pin)
        except:
            pass


def main():
    """테스트용 메인 함수"""
    def motion_callback(detected):
        if detected:
            print("🚨 움직임 감지!")
        else:
            print("✓ 움직임 감지 안 됨")
    
    pir = PIRSensor(pir_pin=22, callback=motion_callback)
    pir.start_monitoring()
    
    try:
        print("PIR 센서 모니터링 시작 (Ctrl+C로 종료)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n모니터링 종료")
    finally:
        pir.cleanup()


if __name__ == "__main__":
    main()
