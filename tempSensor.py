import smbus
import time


class BMP180:
    """BMP180 온습도/기압 센서 드라이버 클래스"""
    
    # 모드 상수
    MODE_ULTRALOWPOWER = 0
    MODE_STANDARD = 1
    MODE_HIGHRES = 2
    MODE_ULTRAHIGHRES = 3
    
    # BMP180의 레지스터
    REGISTER_AC1 = 0xAA
    REGISTER_AC2 = 0xAC
    REGISTER_AC3 = 0xAE
    REGISTER_AC4 = 0xB0
    REGISTER_AC5 = 0xB2
    REGISTER_AC6 = 0xB4
    REGISTER_B1 = 0xB6
    REGISTER_B2 = 0xB8
    REGISTER_MB = 0xBA
    REGISTER_MC = 0xBC
    REGISTER_MD = 0xBE
    
    REGISTER_CONTROL = 0xF4
    REGISTER_TEMPDATA = 0xF6
    REGISTER_PRESSUREDATA = 0xF6
    
    COMMAND_READTEMP = 0x2E
    COMMAND_READPRESSURE = 0x34
    
    # BMP180의 I2C 통신 주소
    DEFAULT_ADDRESS = 0x77
    DEFAULT_BUS = 1
    
    def __init__(self, bus_number=1, address=0x77, mode=MODE_STANDARD):
        """BMP180 센서 초기화
        
        Args:
            bus_number: I2C 버스 번호 (기본값: 1)
            address: 센서 I2C 주소 (기본값: 0x77)
            mode: 측정 모드 (기본값: MODE_STANDARD)
        """
        self.bus = smbus.SMBus(bus_number)
        self.address = address
        self.mode = mode
        
        # 보정 데이터
        self.AC1 = 0
        self.AC2 = 0
        self.AC3 = 0
        self.AC4 = 0
        self.AC5 = 0
        self.AC6 = 0
        self.B1 = 0
        self.B2 = 0
        self.MB = 0
        self.MC = 0
        self.MD = 0
        
        # 초기화
        self._init_calibration_data()
    
    def _read_byte(self, adr):
        """레지스터에서 1바이트를 읽음"""
        return self.bus.read_byte_data(self.address, adr)
    
    def _read_word(self, adr):
        """레지스터에서 2바이트를 읽음"""
        high = self.bus.read_byte_data(self.address, adr)
        low = self.bus.read_byte_data(self.address, adr + 1)
        val = (high << 8) + low
        return val
    
    def _read_word_2c(self, adr):
        """레지스터에서 2바이트를 읽은 후 보정함"""
        val = self._read_word(adr)
        if val >= 0x8000:
            return -((65535 - val) + 1)
        else:
            return val
    
    def _init_calibration_data(self):
        """레지스터에서 보정 데이터를 읽어서 저장"""
        self.AC1 = self._read_word_2c(self.REGISTER_AC1)
        self.AC2 = self._read_word_2c(self.REGISTER_AC2)
        self.AC3 = self._read_word_2c(self.REGISTER_AC3)
        self.AC4 = self._read_word_2c(self.REGISTER_AC4)
        self.AC5 = self._read_word_2c(self.REGISTER_AC5)
        self.AC6 = self._read_word_2c(self.REGISTER_AC6)
        self.B1 = self._read_word_2c(self.REGISTER_B1)
        self.B2 = self._read_word_2c(self.REGISTER_B2)
        self.MB = self._read_word_2c(self.REGISTER_MB)
        self.MC = self._read_word_2c(self.REGISTER_MC)
        self.MD = self._read_word_2c(self.REGISTER_MD)
        
        print("보정 데이터 로드 완료:")
        print(f"  AC1: {self.AC1}  AC2: {self.AC2}  AC3: {self.AC3}")
        print(f"  AC4: {self.AC4}  AC5: {self.AC5}  AC6: {self.AC6}")
        print(f"  B1: {self.B1}  B2: {self.B2}  MB: {self.MB}")
        print(f"  MC: {self.MC}  MD: {self.MD}")
    
    def _read_raw_temperature(self):
        """BMP180에서 보정전 온도 데이터를 읽음"""
        self.bus.write_byte_data(self.address, self.REGISTER_CONTROL, self.COMMAND_READTEMP)
        time.sleep(0.0045)  # Sleep 4.5ms
        raw = self._read_word_2c(self.REGISTER_TEMPDATA)
        print(f"Raw Temperature: 0x{raw & 0xFFFF:04X} ({raw})")
        return raw
    
    
    def _calibrate_temp(self, raw):
        """온도를 보정함"""
        X1 = ((raw - self.AC6) * self.AC5) >> 15
        X2 = (self.MC << 11) // (X1 + self.MD)
        B5 = X1 + X2
        temp = ((B5 + 8) >> 4) / 10.0
        print(f"Calibrated temperature = {temp:.2f} C")
        return temp
    
    def read_temperature(self):
        """온도를 읽음 (°C)"""
        raw = self._read_raw_temperature()
        temp = self._calibrate_temp(raw)
        return temp
    
    def close(self):
        """I2C 버스 종료"""
        if self.bus:
            self.bus.close()


def main():
    """메인 실행 함수"""
    try:
        # BMP180 센서 초기화
        print("BMP180 센서 초기화 중...")
        sensor = BMP180(bus_number=1, address=0x77, mode=BMP180.MODE_STANDARD)
        print("I2C 버스 연결 성공\n")
        
        # 연속 측정
        print("= 센서 데이터 수집 중 (Ctrl+C로 종료) =\n")
        
        while True:
            try:
                # 모든 데이터 읽기
                temp = sensor.read_temperature()
                
                print("=" * 50)
                print(f"온도:  {temp:.2f} °C")
                print("=" * 50)
                print()
                
                time.sleep(1)  # 1초마다 갱신
                
            except KeyboardInterrupt:
                print("\n프로그램 종료")
                break
            except Exception as e:
                print(f"측정 오류: {e}")
                break
        
        sensor.close()
    
    except FileNotFoundError:
        print("오류: I2C 장치를 찾을 수 없습니다.")
        print("- Raspberry Pi에서: raspi-config로 I2C 활성화")
        print("- 일반 PC: I2C 하드웨어가 필요합니다")
        exit(1)
    except OSError as e:
        print(f"센서 연결 오류: {e}")
        print("BMP180 센서가 I2C 주소 0x77에 연결되어 있는지 확인하세요.")
        print("확인 명령: i2cdetect -y 1")
        exit(1)
    except Exception as e:
        print(f"오류 발생: {e}")
        exit(1)


if __name__ == "__main__":
    main()

